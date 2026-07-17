package com.example.pm84scanner

import android.content.Context
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.mutableStateOf
import com.example.pm84scanner.ui.tasks.TasksScreen
import com.example.pm84scanner.ui.tasks.UiTask
import com.example.pm84scanner.ui.theme.Pm84Theme
import kotlin.concurrent.thread

/**
 * WMS vazifalar ro'yxati + offline-sinxron holati (Compose + Material 3).
 * Tarmoq/sinxron logikasi o'zgarmadi — faqat UI Compose'ga ko'chirildi.
 */
class TasksActivity : AppCompatActivity() {

    private val tasks = mutableStateOf<List<UiTask>>(emptyList())
    private val syncLabel = mutableStateOf("…")
    private val loading = mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Pm84Theme {
                TasksScreen(
                    tasks = tasks.value,
                    syncLabel = syncLabel.value,
                    loading = loading.value,
                    onBack = { finish() },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        SyncManager.syncAsync(this) { runOnUiThread { refreshSyncLabel(); loadTasks() } }
        refreshSyncLabel()
        loadTasks()
    }

    private fun refreshSyncLabel() {
        val pending = OfflineQueue(this).size()
        val online = ConnectivityHelper.isOnline(this)
        syncLabel.value = when {
            pending == 0 && online -> "Online · sinxron"
            pending == 0 -> "Offline"
            else -> "Navbatda: $pending operatsiya"
        }
    }

    private fun loadTasks() {
        val prefs = getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        val baseUrl = prefs.getString(WmsApiClient.KEY_WMS_URL, null)
        val token = prefs.getString(WmsApiClient.KEY_WMS_TOKEN, "").orEmpty()
        val wh = prefs.getString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, null)
        if (baseUrl == null || wh == null) return
        if (!ConnectivityHelper.isOnline(this)) return

        loading.value = true
        thread {
            try {
                val raw = WmsApiClient(baseUrl, token).getTasks(wh)
                val mapped = raw.map { t ->
                    val mc = t.payload.optString("marking_code")
                    val qty = t.payload.optInt("qty")
                    val detail = buildString {
                        if (mc.isNotBlank()) append(mc.take(28))
                        if (qty > 0) append("  ·  qty=$qty")
                    }.ifBlank { "—" }
                    UiTask(t.id, t.type, t.status, t.priority, detail)
                }
                runOnUiThread { tasks.value = mapped; loading.value = false }
            } catch (e: Exception) {
                runOnUiThread {
                    loading.value = false
                    android.widget.Toast.makeText(
                        this, "Vazifalar yuklanmadi: ${e.message?.take(60)}",
                        android.widget.Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }
}
