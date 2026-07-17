package com.example.pm84scanner

import android.content.BroadcastReceiver
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.text.InputType
import android.util.Log
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import com.google.android.material.progressindicator.CircularProgressIndicator

class MainActivity : AppCompatActivity() {
    private lateinit var progressBox: CircularProgressIndicator
    private lateinit var progressPallet: CircularProgressIndicator
    private lateinit var progressTransport: CircularProgressIndicator
    private lateinit var tvBoxProgress: TextView
    private lateinit var tvPalletProgress: TextView
    private lateinit var tvTransportProgress: TextView
    private lateinit var columnTransport: View
    private lateinit var rowParentCode: View
    private lateinit var tvLatokLabel: TextView
    private lateinit var tvPaddonLabel: TextView
    private lateinit var tvTransportLabel: TextView
    private lateinit var tvBoxCodeLabel: TextView
    private lateinit var tvUnitsLabel: TextView
    private lateinit var tvBoxCode: TextView
    private lateinit var tvTransportCode: TextView
    private lateinit var tvL2BoxCodeLabel: TextView
    private lateinit var tvCurrentBoxCode: TextView
    private lateinit var tvUnits: TextView
    private lateinit var btnSend: Button
    private lateinit var btnSettings: Button
    private lateinit var btnClearBox: View
    private lateinit var btnClearUnits: View

    private lateinit var scanMode: ScanMode
    private var fromImport = false

    private var boxLimit = DEFAULT_BOX_LIMIT
    private var palletLimit = DEFAULT_PALLET_LIMIT
    private var transportLimit = DEFAULT_TRANSPORT_LIMIT
    private var l3ChildLimit = DEFAULT_L3_CHILD_LIMIT
    private var unitUtilisationEnabled = false

    private var apiKey: String = ""
    private var baseUrl: String = ""
    private var productGroup: String = ""
    private var manufacturerCountry: String = ""
    private var businessPlaceId: Int = 0

    private var currentBoxCode = ""
    private var currentTransportCode = ""
    private val currentUnitCodes = mutableListOf<String>()
    private val completedBoxes = mutableListOf<BoxPayload>()
    private val globalScannedCodes = mutableSetOf<String>()

    private var l3Parent: String? = null
    private val l3Children = mutableListOf<String>()

    private var toneGenerator: ToneGenerator? = null
    private var clipboardManager: ClipboardManager? = null

    private var lastDedupePayload = ""
    private var lastDedupeAtMs: Long = 0L

    private val clipListener = ClipboardManager.OnPrimaryClipChangedListener {
        window?.decorView?.post { readClipboardIfFocused() }
    }

    private val scanReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val action = intent?.action ?: return
            if (!DecodeBroadcastReceiver.SUPPORTED_ACTIONS.contains(action)) return
            val raw = extractRawBarcodeData(intent)
            val normalized = normalizeGs(raw)
            if (normalized.isBlank()) return
            acceptScan(normalized, "broadcast")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        scanMode = parseScanMode(intent.getStringExtra(ScanIntentExtras.SCAN_MODE))
        fromImport = intent.getBooleanExtra(ScanIntentExtras.FROM_IMPORT, false)

        bindViews()
        loadSettings()
        applyScanModeUi()
        resetScanSessionData()
        applyLimitsToProgressBars()
        renderCurrentCodeBlock()
        renderUnitsBlock()
        updateProgressViews()
        updateSendButtonState()

        btnSettings.setOnClickListener { showSettingsDialog() }
        btnSend.setOnClickListener { submitForCurrentMode() }
        btnClearBox.setOnClickListener { clearParentState() }
        btnClearUnits.setOnClickListener {
            currentUnitCodes.clear()
            renderUnitsBlock()
            updateProgressViews()
            updateSendButtonState()
        }
        tvBoxProgress.setOnClickListener {
            when {
                scanMode == ScanMode.PRODUCTION_UNIT_ONLY -> showDonaLimitDialog()
                scanMode == ScanMode.L3_TRANSPORT_CHAIN -> return@setOnClickListener
                else -> showQuickLimitDialog(true)
            }
        }
        tvPalletProgress.setOnClickListener {
            if (scanMode == ScanMode.L3_TRANSPORT_CHAIN) {
                showL3ChildLimitDialog()
            } else {
                showQuickLimitDialog(false)
            }
        }
        tvTransportProgress.setOnClickListener { showTransportLimitDialog() }

        clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        toneGenerator = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 90)
    }

    override fun onResume() {
        super.onResume()
        val filter = IntentFilter()
        DecodeBroadcastReceiver.SUPPORTED_ACTIONS.forEach { filter.addAction(it) }
        registerReceiver(scanReceiver, filter)

        val latestMode = parseScanMode(intent.getStringExtra(ScanIntentExtras.SCAN_MODE))
        val latestFromImport = intent.getBooleanExtra(ScanIntentExtras.FROM_IMPORT, false)
        if (latestMode != scanMode || latestFromImport != fromImport) {
            scanMode = latestMode
            fromImport = latestFromImport
            loadSettings()
            applyScanModeUi()
            resetScanSessionData()
            renderCurrentCodeBlock()
            renderUnitsBlock()
            updateProgressViews()
            updateSendButtonState()
        }
        clipboardManager?.addPrimaryClipChangedListener(clipListener)
    }

    override fun onPause() {
        super.onPause()
        clipboardManager?.removePrimaryClipChangedListener(clipListener)
        try {
            unregisterReceiver(scanReceiver)
        } catch (e: Exception) {
            Log.e(TAG_SCAN, "Receiver not registered", e)
        }
    }

    override fun onDestroy() {
        toneGenerator?.release()
        toneGenerator = null
        super.onDestroy()
    }

    private fun bindViews() {
        progressBox = findViewById(R.id.progressBox)
        progressPallet = findViewById(R.id.progressPallet)
        progressTransport = findViewById(R.id.progressTransport)
        tvBoxProgress = findViewById(R.id.tvBoxProgress)
        tvPalletProgress = findViewById(R.id.tvPalletProgress)
        tvTransportProgress = findViewById(R.id.tvTransportProgress)
        columnTransport = findViewById(R.id.columnTransport)
        rowParentCode = findViewById(R.id.rowParentCode)
        tvLatokLabel = findViewById(R.id.tvLatokLabel)
        tvPaddonLabel = findViewById(R.id.tvPaddonLabel)
        tvTransportLabel = findViewById(R.id.tvTransportLabel)
        tvBoxCodeLabel = findViewById(R.id.tvBoxCodeLabel)
        tvUnitsLabel = findViewById(R.id.tvUnitsLabel)
        tvBoxCode = findViewById(R.id.tvBoxCode)
        tvTransportCode = findViewById(R.id.tvTransportCode)
        tvL2BoxCodeLabel = findViewById(R.id.tvL2BoxCodeLabel)
        tvCurrentBoxCode = findViewById(R.id.tvCurrentBoxCode)
        tvUnits = findViewById(R.id.tvUnits)
        btnSend = findViewById(R.id.btnSend)
        btnSettings = findViewById(R.id.btnSettings)
        btnClearBox = findViewById(R.id.btnClearBox)
        btnClearUnits = findViewById(R.id.btnClearUnits)
    }

    private fun applyScanModeUi() {
        when (scanMode) {
            ScanMode.PRODUCTION_UNIT_ONLY -> {
                columnTransport.visibility = View.GONE
                rowParentCode.visibility = View.GONE
                tvLatokLabel.setText(R.string.dona_progress_label)
                findViewById<View>(R.id.columnPaddon).visibility = View.GONE
                tvBoxCodeLabel.visibility = View.VISIBLE
                tvUnitsLabel.setText(R.string.unit_codes_label)
                tvBoxCode.visibility = View.GONE
                tvTransportCode.visibility = View.GONE
                tvL2BoxCodeLabel.visibility = View.GONE
                tvCurrentBoxCode.visibility = View.GONE
                btnClearBox.visibility = View.GONE
            }
            ScanMode.L1_BOX_UNIT -> {
                columnTransport.visibility = View.GONE
                rowParentCode.visibility = View.VISIBLE
                findViewById<View>(R.id.columnPaddon).visibility = View.VISIBLE
                tvLatokLabel.setText(
                    if (fromImport) R.string.import_progress_label_box else R.string.box_progress_label
                )
                tvPaddonLabel.setText(
                    if (fromImport) R.string.import_progress_label_aik else R.string.pallet_progress_label
                )
                tvBoxCodeLabel.visibility = View.VISIBLE
                tvBoxCodeLabel.setText(
                    if (fromImport) R.string.import_label_current_aik else R.string.box_code_label
                )
                tvUnitsLabel.setText(
                    if (fromImport) R.string.import_label_current_box_codes else R.string.unit_codes_label
                )
                tvBoxCode.visibility = View.VISIBLE
                tvTransportCode.visibility = View.GONE
                tvL2BoxCodeLabel.visibility = View.GONE
                tvCurrentBoxCode.visibility = View.GONE
                btnClearBox.visibility = View.VISIBLE
                btnClearBox.isEnabled = true
            }
            ScanMode.L2_THREE_TIER -> {
                columnTransport.visibility = View.VISIBLE
                rowParentCode.visibility = View.VISIBLE
                findViewById<View>(R.id.columnPaddon).visibility = View.VISIBLE
                tvLatokLabel.setText(R.string.box_progress_label)
                tvPaddonLabel.setText(R.string.pallet_progress_label)
                tvTransportLabel.setText(R.string.transport_progress_label)
                tvBoxCodeLabel.visibility = View.VISIBLE
                tvBoxCodeLabel.setText(R.string.l2_label_transport_code)
                tvUnitsLabel.setText(R.string.unit_codes_label)
                tvBoxCode.visibility = View.GONE
                tvTransportCode.visibility = View.VISIBLE
                tvL2BoxCodeLabel.visibility = View.VISIBLE
                tvCurrentBoxCode.visibility = View.VISIBLE
                btnClearBox.visibility = View.VISIBLE
                btnClearBox.isEnabled = true
            }
            ScanMode.L3_TRANSPORT_CHAIN -> {
                columnTransport.visibility = View.GONE
                rowParentCode.visibility = View.VISIBLE
                findViewById<View>(R.id.columnPaddon).visibility = View.VISIBLE
                tvBoxCodeLabel.visibility = View.VISIBLE
                tvLatokLabel.text = "PARENT"
                tvPaddonLabel.text = "CHILD"
                tvBoxCodeLabel.text = "Parent transport code"
                tvUnitsLabel.text = "Child codes (transport / box / AIK)"
                tvBoxCode.visibility = View.VISIBLE
                tvTransportCode.visibility = View.GONE
                tvL2BoxCodeLabel.visibility = View.GONE
                tvCurrentBoxCode.visibility = View.GONE
                btnClearBox.visibility = View.VISIBLE
                btnClearBox.isEnabled = true
            }
            ScanMode.L1_IMPORT_TRANSPORT -> {
                columnTransport.visibility = View.GONE
                rowParentCode.visibility = View.VISIBLE
                findViewById<View>(R.id.columnPaddon).visibility = View.VISIBLE
                tvBoxCodeLabel.visibility = View.VISIBLE
                tvBoxCodeLabel.setText(R.string.label_parent_transport)
                tvUnitsLabel.setText(R.string.unit_codes_label)
                tvLatokLabel.setText(R.string.box_progress_label)
                tvPaddonLabel.setText(R.string.pallet_progress_label)
                tvBoxCode.visibility = View.VISIBLE
                tvTransportCode.visibility = View.GONE
                tvL2BoxCodeLabel.visibility = View.GONE
                tvCurrentBoxCode.visibility = View.GONE
                btnClearBox.visibility = View.VISIBLE
                btnClearBox.isEnabled = true
            }
        }
    }

    private fun readClipboardIfFocused() {
        if (!hasWindowFocus()) return
        val text = clipboardManager?.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
        val normalized = normalizeGs(text)
        if (normalized.isNotBlank()) acceptScan(normalized, "clipboard")
    }

    private fun acceptScan(code: String, source: String) {
        val now = SystemClock.elapsedRealtime()
        if (code == lastDedupePayload && now - lastDedupeAtMs < DEDUPE_WINDOW_MS) return
        lastDedupePayload = code
        lastDedupeAtMs = now
        Log.d(TAG_SCAN, "Accept scan ($source): $code")
        onScannedCode(code)
    }

    private fun onScannedCode(code: String) {
        val rule = normalizeForRuleCheck(code)
        when (scanMode) {
            ScanMode.PRODUCTION_UNIT_ONLY -> {
                if (!isUnitCode(rule)) return showErrorFeedback(getString(R.string.toast_invalid_format))
                addUnit(code)
            }
            ScanMode.L1_BOX_UNIT -> {
                when {
                    isParentCandidate(rule) -> setParentBox(code)
                    isUnitCandidate(rule) -> addUnitToBox(code)
                    else -> showErrorFeedback(
                        if (fromImport) {
                            if (rule.startsWith("010")) getString(R.string.toast_invalid_import_unit)
                            else getString(R.string.toast_invalid_import_box)
                        } else {
                            getString(R.string.toast_invalid_format)
                        }
                    )
                }
            }
            ScanMode.L2_THREE_TIER -> {
                when {
                    isTransportCode(rule) -> setTransport(code)
                    isBoxCode(rule) -> {
                        if (currentTransportCode.isBlank()) {
                            showErrorFeedback(getString(R.string.toast_scan_transport_parent_first))
                        } else {
                            setParentBox(code)
                        }
                    }
                    isUnitCode(rule) -> addUnitToBox(code)
                    else -> showErrorFeedback(getString(R.string.toast_invalid_format))
                }
            }
            ScanMode.L3_TRANSPORT_CHAIN -> {
                if (l3Parent == null) {
                    if (!isTransportCode(rule)) return showErrorFeedback(getString(R.string.toast_invalid_transport))
                    if (!tryRegisterGlobalCode(code)) return
                    l3Parent = code
                } else {
                    if (!isL3ChildCode(rule)) return showErrorFeedback(getString(R.string.toast_invalid_l3_child))
                    if (!tryRegisterGlobalCode(code)) return
                    l3Children.add(code)
                }
                renderCurrentCodeBlock()
                renderUnitsBlock()
                updateProgressViews()
                updateSendButtonState()
            }
            ScanMode.L1_IMPORT_TRANSPORT -> {
                when {
                    isTransportCode(rule) -> setParentBox(code)
                    isUnitCode(rule) -> addImportUnit(code)
                    else -> showErrorFeedback(getString(R.string.toast_invalid_format))
                }
            }
        }
    }

    private fun setParentBox(code: String) {
        if (currentBoxCode.isNotBlank()) return showErrorFeedback(getString(R.string.toast_box_already_open))
        if (!tryRegisterGlobalCode(code)) return
        currentBoxCode = code
        renderCurrentCodeBlock()
        updateSendButtonState()
    }

    private fun addUnit(code: String) {
        if (!tryRegisterGlobalCode(code)) return
        currentUnitCodes.add(code)
        renderUnitsBlock()
        updateProgressViews()
        updateSendButtonState()
    }

    private fun addUnitToBox(code: String) {
        if (currentBoxCode.isBlank()) return showErrorFeedback(getString(R.string.toast_scan_box_first))
        if (scanMode == ScanMode.L1_BOX_UNIT && currentUnitCodes.size >= boxLimit) {
            return showErrorFeedback(getString(R.string.toast_box_ring_full_send))
        }
        addUnit(code)
        if (currentUnitCodes.size >= boxLimit) finalizeBox()
    }

    private fun addImportUnit(code: String) {
        if (currentBoxCode.isBlank()) return showErrorFeedback(getString(R.string.toast_scan_transport_parent_first))
        addUnit(code)
        if (currentUnitCodes.size >= boxLimit) finalizeBox()
    }

    private fun finalizeBox(suppressVibrate: Boolean = false) {
        completedBoxes.add(BoxPayload(currentBoxCode, currentUnitCodes.toList()))
        currentBoxCode = ""
        currentUnitCodes.clear()
        renderCurrentCodeBlock()
        renderUnitsBlock()
        updateProgressViews()
        updateSendButtonState()
        if (!suppressVibrate) vibrateSuccess()
    }

    private fun setTransport(code: String) {
        if (currentTransportCode.isNotBlank()) return
        if (!tryRegisterGlobalCode(code)) return
        currentTransportCode = code
        renderCurrentCodeBlock()
        updateProgressViews()
    }

    private fun tryRegisterGlobalCode(code: String): Boolean {
        if (globalScannedCodes.contains(code)) {
            showErrorFeedback(getString(R.string.toast_duplicate_scanned_global))
            return false
        }
        globalScannedCodes.add(code)
        return true
    }

    private fun renderCurrentCodeBlock() {
        tvBoxCode.text = when (scanMode) {
            ScanMode.L3_TRANSPORT_CHAIN -> l3Parent.orEmpty()
            ScanMode.PRODUCTION_UNIT_ONLY -> ""
            else -> currentBoxCode.ifBlank { "" }
        }
        if (scanMode == ScanMode.L2_THREE_TIER) {
            tvTransportCode.text = currentTransportCode.ifBlank { "-" }
            tvCurrentBoxCode.text = currentBoxCode.ifBlank { "-" }
        } else {
            tvTransportCode.text = "Current transport: ${currentTransportCode.ifBlank { "-" }}"
            tvCurrentBoxCode.text = "Current box: ${currentBoxCode.ifBlank { "-" }}"
        }
    }

    private fun renderUnitsBlock() {
        tvUnits.text = when (scanMode) {
            ScanMode.L3_TRANSPORT_CHAIN -> if (l3Children.isEmpty()) getString(R.string.l3_child_codes_empty) else l3Children.joinToString("\n")
            else -> if (currentUnitCodes.isEmpty()) {
                if (scanMode == ScanMode.L1_BOX_UNIT && fromImport) {
                    getString(R.string.import_box_codes_empty)
                } else {
                    getString(R.string.unit_codes_empty)
                }
            } else {
                currentUnitCodes.joinToString("\n")
            }
        }
    }

    private fun updateProgressViews() {
        when (scanMode) {
            ScanMode.PRODUCTION_UNIT_ONLY -> {
                setProgress(progressBox, currentUnitCodes.size, boxLimit)
                tvBoxProgress.text = "${currentUnitCodes.size.coerceAtMost(boxLimit)}/$boxLimit"
                findViewById<View>(R.id.columnPaddon).visibility = View.GONE
                columnTransport.visibility = View.GONE
            }
            ScanMode.L2_THREE_TIER -> {
                val completedPaddons = completedBoxes.size
                val transportProgress = completedPaddons / palletLimit.coerceAtLeast(1)
                val paddonProgress = completedPaddons % palletLimit.coerceAtLeast(1)
                setProgress(progressBox, currentUnitCodes.size, boxLimit)
                setProgress(progressPallet, paddonProgress, palletLimit)
                setProgress(progressTransport, transportProgress, transportLimit.coerceAtLeast(1))
                tvBoxProgress.text = "${currentUnitCodes.size.coerceAtMost(boxLimit)}/$boxLimit"
                tvPalletProgress.text = "${paddonProgress.coerceAtMost(palletLimit)}/$palletLimit"
                tvTransportProgress.text = "${transportProgress.coerceAtMost(transportLimit.coerceAtLeast(1))}/${transportLimit.coerceAtLeast(1)}"
            }
            ScanMode.L3_TRANSPORT_CHAIN -> {
                val p = if (l3Parent == null) 0 else 1
                setProgress(progressBox, p, 1)
                setProgress(progressPallet, l3Children.size, l3ChildLimit)
                tvBoxProgress.text = "$p/1"
                tvPalletProgress.text = "${l3Children.size.coerceAtMost(l3ChildLimit)}/$l3ChildLimit"
            }
            ScanMode.L1_BOX_UNIT -> {
                setProgress(progressBox, currentUnitCodes.size, boxLimit)
                setProgress(progressPallet, completedBoxes.size, palletLimit)
                tvBoxProgress.text = "${currentUnitCodes.size.coerceAtMost(boxLimit)}/$boxLimit"
                tvPalletProgress.text = "${completedBoxes.size.coerceAtMost(palletLimit)}/$palletLimit"
            }
            ScanMode.L1_IMPORT_TRANSPORT -> {
                setProgress(progressBox, currentUnitCodes.size, boxLimit)
                setProgress(progressPallet, completedBoxes.size, palletLimit)
                tvBoxProgress.text = "${currentUnitCodes.size.coerceAtMost(boxLimit)}/$boxLimit"
                tvPalletProgress.text = "${completedBoxes.size.coerceAtMost(palletLimit)}/$palletLimit"
            }
        }
    }

    private fun setProgress(indicator: CircularProgressIndicator, current: Int, max: Int) {
        val m = max.coerceAtLeast(1)
        indicator.max = m
        indicator.progress = current.coerceAtMost(m)
        val color = when {
            current <= 0 -> Color.parseColor("#D32F2F")
            current < m -> Color.parseColor("#FFEB3B")
            else -> Color.parseColor("#2E7D32")
        }
        indicator.setIndicatorColor(color)
    }

    private fun clearParentState() {
        when (scanMode) {
            ScanMode.L3_TRANSPORT_CHAIN -> {
                l3Parent = null
                l3Children.clear()
            }
            else -> {
                currentBoxCode = ""
                currentTransportCode = ""
                currentUnitCodes.clear()
            }
        }
        renderCurrentCodeBlock()
        renderUnitsBlock()
        updateProgressViews()
        updateSendButtonState()
    }

    private fun submitForCurrentMode() {
        if (apiKey.isBlank() || baseUrl.isBlank()) {
            Toast.makeText(this, R.string.missing_api_key, Toast.LENGTH_SHORT).show()
            return
        }
        executeSubmit()
    }

    private fun executeSubmit() {
        btnSend.isEnabled = false
        btnSend.setBackgroundColor(Color.parseColor("#FFC107"))

        val client = XtraceApiClient(baseUrl, apiKey)
        val releaseTypeForUtil = resolveReleaseTypeForCurrentMode()
        Thread {
            try {
                when (scanMode) {
                    ScanMode.PRODUCTION_UNIT_ONLY -> {
                        val u = client.postUtilisation(
                            productGroup,
                            businessPlaceId,
                            manufacturerCountry,
                            currentUnitCodes.toList(),
                            releaseTypeForUtil
                        )
                        runOnUiThread { toastResult(u.first, u.second) }
                    }
                    ScanMode.L1_BOX_UNIT -> {
                        if (completedBoxes.isEmpty()) {
                            return@Thread runOnUiThread {
                                Toast.makeText(this, R.string.send_nothing_to_send, Toast.LENGTH_SHORT).show()
                                updateSendButtonState()
                            }
                        }
                        if (unitUtilisationEnabled) {
                            val utilisationCodes = completedBoxes.flatMap { payload ->
                                if (scanMode == ScanMode.L1_BOX_UNIT && fromImport) payload.units else payload.units + payload.boxCode
                            }
                            val util = client.postUtilisation(
                                productGroup = productGroup,
                                businessPlaceId = businessPlaceId,
                                manufacturerCountry = manufacturerCountry,
                                sntinCodes = utilisationCodes,
                                releaseType = releaseTypeForUtil
                            )
                            if (util.first !in 200..299) {
                                return@Thread runOnUiThread { toastResult(util.first, util.second) }
                            }
                        }
                        val result = client.postAggregation(
                            businessPlaceId = businessPlaceId,
                            boxLimit = boxLimit,
                            completedBoxes = completedBoxes
                        )
                        if (result.first !in 200..299) {
                            return@Thread runOnUiThread { toastResult(result.first, result.second) }
                        }
                        runOnUiThread { toastResult(200, "") }
                    }
                    ScanMode.L2_THREE_TIER -> {
                        if (currentTransportCode.isBlank()) {
                            return@Thread runOnUiThread {
                                showErrorFeedback(getString(R.string.toast_scan_transport_parent_first))
                            }
                        }
                        if (completedBoxes.isEmpty()) {
                            return@Thread runOnUiThread {
                                Toast.makeText(this, R.string.send_nothing_to_send, Toast.LENGTH_SHORT).show()
                                updateSendButtonState()
                            }
                        }
                        if (unitUtilisationEnabled) {
                            val utilisationCodes = completedBoxes.flatMap { payload ->
                                payload.units + payload.boxCode
                            }
                            val util = client.postUtilisation(
                                productGroup = productGroup,
                                businessPlaceId = businessPlaceId,
                                manufacturerCountry = manufacturerCountry,
                                sntinCodes = utilisationCodes,
                                releaseType = releaseTypeForUtil
                            )
                            if (util.first !in 200..299) {
                                return@Thread runOnUiThread { toastResult(util.first, util.second) }
                            }
                        }
                        val agg1 = client.postAggregation(
                            businessPlaceId = businessPlaceId,
                            boxLimit = boxLimit,
                            completedBoxes = completedBoxes
                        )
                        if (agg1.first !in 200..299) {
                            return@Thread runOnUiThread { toastResult(agg1.first, agg1.second) }
                        }
                        val boxCodes = completedBoxes.map { it.boxCode }
                        val agg2 = client.postAggregationTransportToBoxes(
                            businessPlaceId = businessPlaceId,
                            transportCode = currentTransportCode,
                            boxCodes = boxCodes,
                            palletCapacity = palletLimit
                        )
                        runOnUiThread { toastResult(agg2.first, agg2.second) }
                    }
                    ScanMode.L3_TRANSPORT_CHAIN -> {
                        val a = client.postAggregationParentWithChildren(businessPlaceId, l3Parent.orEmpty(), l3Children.toList(), l3ChildLimit)
                        runOnUiThread { toastResult(a.first, a.second) }
                    }
                    ScanMode.L1_IMPORT_TRANSPORT -> {
                        if (completedBoxes.isEmpty()) {
                            return@Thread runOnUiThread {
                                Toast.makeText(this, R.string.send_nothing_to_send, Toast.LENGTH_SHORT).show()
                                updateSendButtonState()
                            }
                        }
                        if (unitUtilisationEnabled) {
                            val utilisationCodes = completedBoxes.flatMap { payload ->
                                payload.units
                            }
                            val util = client.postUtilisation(
                                productGroup = productGroup,
                                businessPlaceId = businessPlaceId,
                                manufacturerCountry = manufacturerCountry,
                                sntinCodes = utilisationCodes,
                                releaseType = releaseTypeForUtil
                            )
                            if (util.first !in 200..299) {
                                return@Thread runOnUiThread { toastResult(util.first, util.second) }
                            }
                        }
                        if (completedBoxes.any { it.boxCode.startsWith("00").not() }) {
                            return@Thread runOnUiThread { showErrorFeedback(getString(R.string.toast_invalid_transport)) }
                        }
                        val a = client.postAggregation(
                            businessPlaceId = businessPlaceId,
                            boxLimit = boxLimit,
                            completedBoxes = completedBoxes
                        )
                        if (a.first !in 200..299) {
                            return@Thread runOnUiThread { toastResult(a.first, a.second) }
                        }
                        runOnUiThread { toastResult(200, "") }
                    }
                }
            } catch (e: Throwable) {
                runOnUiThread {
                    Toast.makeText(this, "Send xatosi: ${e.message}", Toast.LENGTH_SHORT).show()
                    updateSendButtonState()
                }
            }
        }.start()
    }

    private fun toastResult(code: Int, responseBody: String = "") {
        val ok = code in 200..299
        if (ok) {
            performFullReset()
        } else {
            updateSendButtonState()
        }
        val text = if (ok) {
            getString(R.string.send_success)
        } else {
            val details = responseBody.trim().take(220)
            if (details.isNotBlank()) "HTTP $code: $details" else "HTTP $code"
        }
        Toast.makeText(this, text, Toast.LENGTH_LONG).show()
    }

    private fun showSettingsDialog() {
        val scroll = ScrollView(this)
        val container = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(40, 20, 40, 20) }
        val apiKeyInput = EditText(this).apply { hint = getString(R.string.hint_api_key); setText(apiKey) }
        val baseUrlInput = EditText(this).apply { hint = getString(R.string.hint_base_url); setText(baseUrl) }
        val productGroupInput = EditText(this).apply { hint = getString(R.string.hint_product_group); setText(productGroup) }
        val countryInput = EditText(this).apply { hint = getString(R.string.hint_manufacturer_country); setText(manufacturerCountry) }
        val placeInput = EditText(this).apply { hint = getString(R.string.hint_business_place_id); inputType = InputType.TYPE_CLASS_NUMBER; setText(businessPlaceId.toString()) }
        val utilSwitch = SwitchCompat(this).apply {
            text = getString(R.string.settings_unit_utilisation)
            isChecked = unitUtilisationEnabled
            visibility = if (supportsUnitUtilisationSwitch()) View.VISIBLE else View.GONE
        }
        // WMS sozlamalari (putaway uchun)
        val wmsPrefs = getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        val wmsUrlInput = EditText(this).apply {
            hint = getString(R.string.hint_wms_url)
            setText(wmsPrefs.getString(WmsApiClient.KEY_WMS_URL, ""))
        }
        val wmsEmailInput = EditText(this).apply {
            hint = getString(R.string.hint_wms_email)
            inputType = InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
            setText(wmsPrefs.getString(WmsApiClient.KEY_WMS_EMAIL, ""))
        }
        val wmsPasswordInput = EditText(this).apply {
            hint = getString(R.string.hint_wms_password)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setText(wmsPrefs.getString(WmsApiClient.KEY_WMS_PASSWORD, ""))
        }
        val wmsWarehouseInput = EditText(this).apply {
            hint = getString(R.string.hint_wms_warehouse_id)
            setText(wmsPrefs.getString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, ""))
        }

        addLabeledField(container, "API Key", apiKeyInput)
        addLabeledField(container, "Base URL", baseUrlInput)
        addLabeledField(container, "Product Group", productGroupInput)
        addLabeledField(container, "Manufacturer Country", countryInput)
        addLabeledField(container, "Business Place ID", placeInput)
        container.addView(
            utilSwitch,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = 8 }
        )

        // WMS bo'lim sarlavhasi
        container.addView(TextView(this).apply {
            text = "── ${getString(R.string.settings_wms_section)} ──"
            setTextColor(Color.parseColor("#1565C0"))
            textSize = 13f
            setPadding(0, 24, 0, 8)
        })
        addLabeledField(container, "WMS URL", wmsUrlInput)
        addLabeledField(container, "WMS Email", wmsEmailInput)
        addLabeledField(container, "WMS Parol", wmsPasswordInput)
        addLabeledField(container, "WMS Warehouse ID", wmsWarehouseInput)

        scroll.addView(container)
        AlertDialog.Builder(this)
            .setTitle(R.string.settings_title)
            .setView(scroll)
            .setPositiveButton(R.string.save) { _, _ ->
                apiKey = apiKeyInput.text.toString().trim()
                baseUrl = baseUrlInput.text.toString().trim()
                productGroup = productGroupInput.text.toString().trim()
                manufacturerCountry = countryInput.text.toString().trim()
                businessPlaceId = placeInput.text.toString().toIntOrNull() ?: AppConfig.DEFAULT_BUSINESS_PLACE_ID
                unitUtilisationEnabled = utilSwitch.isChecked
                saveSettings()
                applyLimitsToProgressBars()
                updateProgressViews()
                updateSendButtonState()

                // WMS sozlamalarini saqlash (token tozalanadi — yangi login kerak)
                wmsPrefs.edit()
                    .putString(WmsApiClient.KEY_WMS_URL, wmsUrlInput.text.toString().trim())
                    .putString(WmsApiClient.KEY_WMS_EMAIL, wmsEmailInput.text.toString().trim())
                    .putString(WmsApiClient.KEY_WMS_PASSWORD, wmsPasswordInput.text.toString().trim())
                    .putString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, wmsWarehouseInput.text.toString().trim())
                    .remove(WmsApiClient.KEY_WMS_TOKEN)  // yangi parolda eski token bekor
                    .apply()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun addLabeledField(container: LinearLayout, title: String, field: EditText) {
        val label = TextView(this).apply {
            text = title
            setTextColor(Color.parseColor("#0D1B2A"))
            textSize = 13f
        }
        container.addView(label)
        container.addView(
            field,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = 16 }
        )
    }

    private fun showQuickLimitDialog(isBoxLimit: Boolean) {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(if (isBoxLimit) boxLimit.toString() else palletLimit.toString())
        }
        AlertDialog.Builder(this)
            .setTitle(if (isBoxLimit) R.string.quick_edit_box else R.string.quick_edit_pallet)
            .setView(input)
            .setPositiveButton(R.string.save) { _, _ ->
                val value = input.text.toString().toIntOrNull() ?: return@setPositiveButton
                if (isBoxLimit) boxLimit = value else palletLimit = value
                applyLimitsToProgressBars()
                updateProgressViews()
                updateSendButtonState()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun showTransportLimitDialog() {
        if (scanMode != ScanMode.L2_THREE_TIER) return
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            setText(transportLimit.toString())
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.quick_edit_transport)
            .setView(input)
            .setPositiveButton(R.string.save) { _, _ ->
                transportLimit = input.text.toString().toIntOrNull() ?: transportLimit
                updateProgressViews()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun showDonaLimitDialog() {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            hint = "Donalarni kiriting:"
            setText(boxLimit.toString())
        }
        AlertDialog.Builder(this)
            .setTitle("Donalarni kiriting:")
            .setView(input)
            .setPositiveButton(R.string.save) { _, _ ->
                boxLimit = (input.text.toString().toIntOrNull() ?: boxLimit).coerceAtLeast(1)
                updateProgressViews()
                updateSendButtonState()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun showL3ChildLimitDialog() {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER
            hint = "Bola kodlar soni"
            setText(l3ChildLimit.toString())
        }
        AlertDialog.Builder(this)
            .setTitle("Bola kodlar soni")
            .setView(input)
            .setPositiveButton(R.string.save) { _, _ ->
                l3ChildLimit = (input.text.toString().toIntOrNull() ?: l3ChildLimit).coerceAtLeast(1)
                updateProgressViews()
                updateSendButtonState()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun resetScanSessionData() {
        currentBoxCode = ""
        currentTransportCode = ""
        currentUnitCodes.clear()
        completedBoxes.clear()
        l3Parent = null
        l3Children.clear()
    }

    private fun performFullReset() {
        globalScannedCodes.clear()
        resetScanSessionData()
        renderCurrentCodeBlock()
        renderUnitsBlock()
        updateProgressViews()
        updateSendButtonState()
    }

    private fun applyLimitsToProgressBars() {
        progressBox.max = boxLimit.coerceAtLeast(1)
        progressPallet.max = palletLimit.coerceAtLeast(1)
        progressTransport.max = transportLimit.coerceAtLeast(1)
    }

    private fun loadSettings() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        boxLimit = prefs.getInt(KEY_BOX_LIMIT, DEFAULT_BOX_LIMIT)
        palletLimit = prefs.getInt(KEY_PALLET_LIMIT, DEFAULT_PALLET_LIMIT)
        transportLimit = prefs.getInt(KEY_TRANSPORT_LIMIT, DEFAULT_TRANSPORT_LIMIT)
        l3ChildLimit = prefs.getInt(KEY_L3_CHILD_LIMIT, DEFAULT_L3_CHILD_LIMIT)
        apiKey = prefs.getString(KEY_API_KEY, AppConfig.DEFAULT_API_KEY).orEmpty()
        baseUrl = prefs.getString(KEY_BASE_URL, AppConfig.DEFAULT_BASE_URL).orEmpty()
        productGroup = prefs.getString(KEY_PRODUCT_GROUP, AppConfig.DEFAULT_PRODUCT_GROUP).orEmpty()
        val countryKey = if (isImportFlowMode()) KEY_MANUFACTURER_COUNTRY_IMPORT else KEY_MANUFACTURER_COUNTRY
        val defaultCountry = if (isImportFlowMode()) AppConfig.DEFAULT_IMPORT_MANUFACTURER_COUNTRY else AppConfig.DEFAULT_MANUFACTURER_COUNTRY
        manufacturerCountry = prefs.getString(countryKey, defaultCountry).orEmpty()
        businessPlaceId = prefs.getInt(KEY_BUSINESS_PLACE_ID, AppConfig.DEFAULT_BUSINESS_PLACE_ID)
        unitUtilisationEnabled = prefs.getBoolean(KEY_UNIT_UTILISATION, false)
    }

    private fun saveSettings() {
        getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit()
            .putInt(KEY_BOX_LIMIT, boxLimit)
            .putInt(KEY_PALLET_LIMIT, palletLimit)
            .putInt(KEY_TRANSPORT_LIMIT, transportLimit)
            .putInt(KEY_L3_CHILD_LIMIT, l3ChildLimit)
            .putString(KEY_API_KEY, apiKey)
            .putString(KEY_BASE_URL, baseUrl)
            .putString(KEY_PRODUCT_GROUP, productGroup)
            .putString(
                if (isImportFlowMode()) KEY_MANUFACTURER_COUNTRY_IMPORT else KEY_MANUFACTURER_COUNTRY,
                manufacturerCountry
            )
            .putInt(KEY_BUSINESS_PLACE_ID, businessPlaceId)
            .putBoolean(KEY_UNIT_UTILISATION, unitUtilisationEnabled)
            .apply()
    }

    private fun updateSendButtonState() {
        val enabled = when (scanMode) {
            ScanMode.PRODUCTION_UNIT_ONLY -> currentUnitCodes.size >= boxLimit
            ScanMode.L1_BOX_UNIT -> completedBoxes.size >= palletLimit
            ScanMode.L2_THREE_TIER -> {
                val completedPaddons = completedBoxes.size
                val transportProgress = completedPaddons / palletLimit.coerceAtLeast(1)
                transportProgress >= transportLimit.coerceAtLeast(1)
            }
            ScanMode.L3_TRANSPORT_CHAIN -> l3Parent != null && l3Children.size >= l3ChildLimit
            ScanMode.L1_IMPORT_TRANSPORT -> completedBoxes.size >= palletLimit
        }
        btnSend.isEnabled = enabled
        btnSend.setBackgroundColor(if (enabled) Color.parseColor("#1F4FA3") else Color.parseColor("#9E9E9E"))
    }

    private fun supportsUnitUtilisationSwitch(): Boolean = when (scanMode) {
        ScanMode.L1_BOX_UNIT, ScanMode.L2_THREE_TIER, ScanMode.L1_IMPORT_TRANSPORT -> true
        else -> false
    }

    private fun isImportFlowMode(): Boolean =
        scanMode == ScanMode.L1_IMPORT_TRANSPORT || (scanMode == ScanMode.L1_BOX_UNIT && fromImport)

    private fun resolveReleaseTypeForCurrentMode(): String {
        if (!unitUtilisationEnabled) return AppConfig.RELEASE_TYPE
        return if (isImportFlowMode()) IMPORT_RELEASE_TYPE else AppConfig.RELEASE_TYPE
    }

    private fun showErrorFeedback(message: String) {
        tvUnits.setBackgroundColor(Color.parseColor("#FFE4E4"))
        tvUnits.postDelayed({ tvUnits.setBackgroundColor(Color.parseColor("#E8EEF8")) }, 220)
        playErrorTone()
        vibrateError()
        updateSendButtonState()
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    private fun playErrorTone() {
        try {
            toneGenerator?.startTone(ToneGenerator.TONE_PROP_NACK, 200)
        } catch (_: Throwable) {
        }
    }

    private fun vibrateSuccess() = vibrate(100)
    private fun vibrateError() = vibrate(70)

    private fun vibrate(durationMs: Long) {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(VIBRATOR_SERVICE) as Vibrator
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(durationMs)
        }
    }

    private fun normalizeGs(raw: String): String = raw.replace(Regex("[\\u001D]"), "<GS>").trim()
    private fun normalizeForRuleCheck(code: String): String = code.replace("<GS>", "").replace(" ", "").trimStart { !it.isDigit() }
    private fun isBoxCode(code: String): Boolean = code.startsWith("01") && code.length > 2 && code[2] != '0'
    private fun isUnitCode(code: String): Boolean = code.startsWith("010")
    private fun isTransportCode(code: String): Boolean = code.length == 20 && code.startsWith("00") && code.all { it.isDigit() }
    private fun isL3ChildCode(code: String): Boolean =
        isTransportCode(code) || isBoxCode(code) || isImportBoxCode25(code)

    /** Import > Box AIK: 00000…, dastlabki 25 ta belgi raqam (keyingi qismi serial/chek bo‘lishi mumkin). */
    private fun isImportBoxCode25(rule: String): Boolean =
        rule.length >= 25 && rule.startsWith("00000") && rule.take(25).all { it.isDigit() }

    /** Import > Box: to‘liq GS1 birlik (010…), qat’iy 25 raqam talabi yo‘q. */
    private fun isImportUnitCode25(rule: String): Boolean =
        rule.startsWith("010") && rule.length >= 14

    private fun isParentCandidate(rule: String): Boolean =
        if (fromImport) isImportBoxCode25(rule) else isBoxCode(rule)

    private fun isUnitCandidate(rule: String): Boolean =
        if (fromImport) isImportUnitCode25(rule) else isUnitCode(rule)

    private fun extractRawBarcodeData(intent: Intent): String {
        val keys = listOf(
            DecodeBroadcastReceiver.EXTRA_DATA,
            "EXTRA_EVENT_DECODE_STRING_VALUE",
            "barcode_string",
            "data",
            "DATA"
        )
        keys.forEach { k -> intent.getStringExtra(k)?.trim()?.takeIf { it.isNotEmpty() }?.let { return it } }
        return ""
    }

    companion object {
        private const val DEDUPE_WINDOW_MS = 900L
        private const val TAG_SCAN = "PM84_SCAN_UI"
        private const val PREFS_NAME = "enasai_settings"
        private const val KEY_BOX_LIMIT = "box_limit"
        private const val KEY_PALLET_LIMIT = "pallet_limit"
        private const val KEY_TRANSPORT_LIMIT = "transport_limit"
        private const val KEY_L3_CHILD_LIMIT = "l3_child_limit"
        private const val KEY_API_KEY = "api_key"
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_PRODUCT_GROUP = "product_group"
        private const val KEY_MANUFACTURER_COUNTRY = "manufacturer_country"
        private const val KEY_MANUFACTURER_COUNTRY_IMPORT = "manufacturer_country_import"
        private const val KEY_BUSINESS_PLACE_ID = "business_place_id"
        private const val KEY_UNIT_UTILISATION = "unit_utilisation"
        private const val IMPORT_RELEASE_TYPE = "IMPORT"
        private const val DEFAULT_BOX_LIMIT = 12
        private const val DEFAULT_PALLET_LIMIT = 85
        private const val DEFAULT_TRANSPORT_LIMIT = 1
        private const val DEFAULT_L3_CHILD_LIMIT = 1
    }
}
