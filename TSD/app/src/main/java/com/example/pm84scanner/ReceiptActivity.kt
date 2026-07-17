package com.example.pm84scanner

import com.example.pm84scanner.ui.theme.FlowReceipt
import kotlin.concurrent.thread

/**
 * Kirim (receipt): operator transport (pallet/SSCC) kodlarini skanlaydi,
 * ro'yxat to'planadi, "Yuborish" bosilganda WMS /receipt ga (offline-aware)
 * yuboriladi — backend owner-check qiladi, putaway task(lar) yaratadi.
 */
class ReceiptActivity : ScanBaseActivity() {

    private val codes = linkedSetOf<String>()

    override fun screenTitle() = "Kirim (pallet skan)"
    override fun initialHint() = "Transport/pallet kodini skanlang"
    override fun accent() = FlowReceipt

    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        setButtons(primary = "Yuborish", secondary = "Tozalash")
        onSecondary = { codes.clear(); clearLog(); updateCounter() }
        onPrimary = { submit() }
        updateCounter()
    }

    override fun onScan(raw: String) {
        if (raw.length < 8) { toastUi("Kod juda qisqa"); return }
        if (codes.add(raw)) {
            vibrateOk()
            logLine("• ${raw.take(34)}")
            updateCounter()
        } else {
            toastUi("Bu kod allaqachon qo'shilgan")
        }
    }

    private fun updateCounter() = setCounter("Skanlangan: ${codes.size}")

    private fun submit() {
        if (codes.isEmpty()) { toastUi("Avval kod skanlang"); return }
        if (warehouseId.isBlank()) { toastUi("Sklad tanlanmagan (sozlamalar)"); return }
        val list = codes.map { it to guessPackageType(it) }
        setPrimaryEnabled(false)
        setCounter("Yuborilmoqda… (${codes.size} kod)")
        thread {
            val res = WmsOps.receipt(this, warehouseId, list)
            runOnUiThread {
                setPrimaryEnabled(true)
                when (res.outcome) {
                    WmsOps.Outcome.SENT -> {
                        vibrateOk()
                        toastUi("Qabul qilindi ✓ (${list.size} kod)")
                        codes.clear(); clearLog(); updateCounter()
                    }
                    WmsOps.Outcome.QUEUED -> {
                        toastUi("Offline rejim — ${list.size} kod navbatga saqlandi")
                        codes.clear(); clearLog(); updateCounter()
                    }
                    WmsOps.Outcome.FAILED -> toastUi("Xatolik: ${res.detail.take(80)}")
                }
            }
        }
    }

    private fun guessPackageType(code: String): String =
        if (code.startsWith("00")) "BOX_LV_1" else "BOX_LV_1"
}
