package com.example.pm84scanner

import com.example.pm84scanner.ui.theme.FlowInventory
import kotlin.concurrent.thread

/**
 * Inventarizatsiya (cycle/full count): operator mahsulot kodlarini skanlaydi,
 * GTIN bo'yicha mahsulot aniqlanadi va miqdor sanaladi. "Yuborish" → WMS
 * /inventory/count (offline-aware); backend farqlarni hisoblab ledger yozadi.
 */
class InventoryActivity : ScanBaseActivity() {

    // productId -> (name, counted)
    private val counts = linkedMapOf<String, Pair<String, Int>>()

    override fun screenTitle() = "Inventarizatsiya"
    override fun initialHint() = "Mahsulot kodini (DataMatrix) skanlang"
    override fun accent() = FlowInventory

    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        setButtons(primary = "Yuborish", secondary = "Tozalash")
        onSecondary = { counts.clear(); clearLog(); updateCounter() }
        onPrimary = { submit() }
        updateCounter()
    }

    override fun onScan(raw: String) {
        when (classifyCode(raw)) {
            CodeKind.TRANSPORT -> {
                toastUi("Transport kodi — putaway yoki qabul oqimida ishlating")
                return
            }
            CodeKind.UNKNOWN -> {
                toastUi("Noma'lum kod formati (00… yoki 01… kutilgan)")
                return
            }
            else -> { /* UNIT yoki BOX — davom etamiz */ }
        }
        val gtin = extractGtin(raw)
        if (gtin == null) { toastUi("GTIN ajratib olinmadi"); return }
        thread {
            val p = client().productByGtin(gtin)
            runOnUiThread {
                if (p == null) { toastUi("GTIN $gtin WMS da topilmadi"); return@runOnUiThread }
                val prev = counts[p.id]
                val qty = (prev?.second ?: 0) + 1
                counts[p.id] = p.name to qty
                vibrateOk()
                redraw()
            }
        }
    }

    private fun redraw() {
        clearLog()
        for ((_, v) in counts) logLine("• ${v.first}:  ${v.second}")
        updateCounter()
    }

    private fun updateCounter() =
        setCounter("Mahsulot turi: ${counts.size}  ·  jami: ${counts.values.sumOf { it.second }}")

    private fun submit() {
        if (counts.isEmpty()) { toastUi("Avval skanlang"); return }
        if (warehouseId.isBlank()) { toastUi("Sklad tanlanmagan"); return }
        val lines = counts.map { (pid, v) -> Triple(pid, null as String?, v.second) }
        setPrimaryEnabled(false)
        thread {
            val res = WmsOps.inventoryCount(this, warehouseId, lines)
            runOnUiThread {
                setPrimaryEnabled(true)
                when (res.outcome) {
                    WmsOps.Outcome.SENT -> { toastUi("Inventar yuborildi ✓"); counts.clear(); redraw() }
                    WmsOps.Outcome.QUEUED -> { toastUi("Offline — navbatga saqlandi"); counts.clear(); redraw() }
                    WmsOps.Outcome.FAILED -> toastUi("Xatolik: ${res.detail.take(80)}")
                }
            }
        }
    }
}
