package com.example.pm84scanner

import android.content.Context
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.mutableStateOf
import com.example.pm84scanner.ui.picking.PickingScreen
import com.example.pm84scanner.ui.picking.UiOrder
import com.example.pm84scanner.ui.theme.Pm84Theme
import kotlin.concurrent.thread

/**
 * Terish / Otgruzka (Compose + Material 3). Smartup'dan ochiq buyurtmalar yuklanadi;
 * operator buyurtmani tanlaydi → pick-task (FEFO reja) → "Yakunlash" bilan tasdiqlash.
 * Tarmoq logikasi (WmsApiClient) o'zgarmadi.
 */
class PickingActivity : AppCompatActivity() {

    private val orders = mutableStateOf<List<UiOrder>>(emptyList())
    private val statusText = mutableStateOf("")
    private val loading = mutableStateOf(false)
    private val confirm = mutableStateOf<Pair<String, String>?>(null)

    private var baseUrl = ""
    private var token = ""
    private var warehouseId = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        loadPrefs()
        setContent {
            Pm84Theme {
                PickingScreen(
                    orders = orders.value,
                    statusText = statusText.value,
                    loading = loading.value,
                    confirm = confirm.value,
                    onRefresh = { confirm.value = null; loadOrders() },
                    onSelect = ::createTask,
                    onConfirm = ::confirmDoc,
                    onBack = { finish() },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        loadPrefs()
        SyncManager.syncAsync(this)
        loadOrders()
    }

    private fun loadPrefs() {
        val p = getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        baseUrl = p.getString(WmsApiClient.KEY_WMS_URL, "").orEmpty()
        token = p.getString(WmsApiClient.KEY_WMS_TOKEN, "").orEmpty()
        warehouseId = p.getString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, "").orEmpty()
    }

    private fun client() = WmsApiClient(baseUrl, token)

    private fun toast(msg: String) =
        runOnUiThread { android.widget.Toast.makeText(this, msg, android.widget.Toast.LENGTH_SHORT).show() }

    private fun loadOrders() {
        if (warehouseId.isBlank()) { toast("Sklad tanlanmagan"); return }
        if (!ConnectivityHelper.isOnline(this)) { toast("Internet aloqasi yo'q"); return }
        loading.value = true
        statusText.value = "Yuklanmoqda…"
        thread {
            try {
                val list = client().getShipmentOrders(warehouseId)
                    .map { UiOrder(it.dealId, it.number, it.status) }
                runOnUiThread {
                    orders.value = list
                    statusText.value = "Buyurtmalar: ${list.size}"
                    loading.value = false
                }
            } catch (e: Exception) {
                runOnUiThread { loading.value = false; toast("Yuklanmadi: ${e.message?.take(60)}") }
            }
        }
    }

    private fun createTask(order: UiOrder) {
        toast("Terish rejasi yaratilmoqda…")
        thread {
            val docId = client().createPickTask(warehouseId, order.dealId)
            runOnUiThread {
                if (docId == null) { toast("Reja yaratilmadi"); return@runOnUiThread }
                vibrateOk()
                confirm.value = docId to "Buyurtma №${order.number.ifBlank { order.dealId }}"
            }
        }
    }

    private fun confirmDoc(docId: String) {
        toast("Yakunlanmoqda…")
        thread {
            val ok = client().confirmShipmentDoc(docId)
            runOnUiThread {
                if (ok) {
                    vibrateOk(); toast("Otgruzka yakunlandi ✓ (Smartup'ga yuborildi)")
                    confirm.value = null; loadOrders()
                } else toast("Yakunlashda xatolik")
            }
        }
    }

    private fun vibrateOk() {
        val v = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            (getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as android.os.VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION") getSystemService(Context.VIBRATOR_SERVICE) as android.os.Vibrator
        }
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            v.vibrate(android.os.VibrationEffect.createOneShot(60, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION") v.vibrate(60)
        }
    }
}
