package com.example.pm84scanner

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.text.InputType
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.mutableStateOf
import com.example.pm84scanner.ui.dashboard.DashboardScreen
import com.example.pm84scanner.ui.dashboard.SyncState
import com.example.pm84scanner.ui.theme.Pm84Theme

/**
 * Bosh ekran — endi Jetpack Compose (Material 3). Eski XML ekranlar (Putaway,
 * Receipt, ...) Intent orqali ochiladi; ular bosqichma-bosqich Compose'ga ko'chiriladi.
 */
class MainDashboardActivity : AppCompatActivity() {

    private val syncState = mutableStateOf<SyncState>(SyncState.Offline(0))

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Pm84Theme {
                DashboardScreen(
                    sync = syncState.value,
                    warehouseName = null,
                    onAction = ::openFlow,
                    onSettings = ::showWmsSettingsDialog,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        SyncManager.syncAsync(this) { runOnUiThread { updateSyncStatus() } }
        updateSyncStatus()
    }

    private fun updateSyncStatus() {
        val pending = OfflineQueue(this).size()
        val online = ConnectivityHelper.isOnline(this)
        syncState.value =
            if (online) SyncState.Online(pending) else SyncState.Offline(pending)
    }

    private fun openFlow(route: String) {
        val target = when (route) {
            "production" -> ProductionMenuActivity::class.java
            "check" -> CheckSingleActivity::class.java
            "import" -> ImportMenuActivity::class.java
            "putaway" -> PutawayActivity::class.java
            "receipt" -> ReceiptActivity::class.java
            "picking" -> PickingActivity::class.java
            "inventory" -> InventoryActivity::class.java
            "tasks" -> TasksActivity::class.java
            else -> return
        }
        startActivity(Intent(this, target))
    }

    /** WMS sozlamalari (URL / Email / Parol / Warehouse ID) — barcha WMS ekranlari shundan o'qiydi. */
    private fun showWmsSettingsDialog() {
        val p = getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        val urlInput = EditText(this).apply {
            hint = "https://server:8000 (yoki domen)"
            setText(p.getString(WmsApiClient.KEY_WMS_URL, ""))
        }
        val emailInput = EditText(this).apply {
            hint = "admin@wms.uz"
            inputType = InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
            setText(p.getString(WmsApiClient.KEY_WMS_EMAIL, ""))
        }
        val passInput = EditText(this).apply {
            hint = "parol"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setText(p.getString(WmsApiClient.KEY_WMS_PASSWORD, ""))
        }
        val whInput = EditText(this).apply {
            hint = "Warehouse ID (UUID)"
            setText(p.getString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, ""))
        }

        fun labeled(title: String, field: EditText) = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 12, 0, 0)
            addView(TextView(this@MainDashboardActivity).apply { text = title; textSize = 12f })
            addView(field)
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 16, 48, 8)
            addView(labeled("WMS URL", urlInput))
            addView(labeled("WMS Email", emailInput))
            addView(labeled("WMS Parol", passInput))
            addView(labeled("WMS Warehouse ID", whInput))
        }

        AlertDialog.Builder(this)
            .setTitle("WMS sozlamalari")
            .setView(ScrollView(this).apply { addView(container) })
            .setPositiveButton("Saqlash") { _, _ ->
                p.edit()
                    .putString(WmsApiClient.KEY_WMS_URL, urlInput.text.toString().trim().trimEnd('/'))
                    .putString(WmsApiClient.KEY_WMS_EMAIL, emailInput.text.toString().trim())
                    .putString(WmsApiClient.KEY_WMS_PASSWORD, passInput.text.toString())
                    .putString(WmsApiClient.KEY_WMS_WAREHOUSE_ID, whInput.text.toString().trim())
                    .remove(WmsApiClient.KEY_WMS_TOKEN)
                    .apply()
                Toast.makeText(this, "WMS sozlamalari saqlandi", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Bekor", null)
            .show()
    }
}
