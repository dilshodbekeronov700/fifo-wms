package com.example.pm84scanner

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.LocalShipping
import com.example.pm84scanner.ui.menu.MenuItem
import com.example.pm84scanner.ui.menu.MenuScreen
import com.example.pm84scanner.ui.theme.FlowImport
import com.example.pm84scanner.ui.theme.Pm84Theme

class ImportMenuActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Pm84Theme {
                MenuScreen(
                    title = "Import",
                    accent = FlowImport,
                    onBack = { finish() },
                    items = listOf(
                        MenuItem("Box", "Quti + birliklar (L1)", Icons.Filled.Inventory, FlowImport) {
                            startActivity(
                                Intent(this, MainActivity::class.java)
                                    .putExtra(ScanIntentExtras.SCAN_MODE, ScanMode.L1_BOX_UNIT.name)
                                    .putExtra(ScanIntentExtras.FROM_IMPORT, true)
                            )
                        },
                        MenuItem("Transport", "Transport + birliklar", Icons.Filled.LocalShipping, FlowImport) {
                            startActivity(Intent(this, MainActivity::class.java)
                                .putExtra(ScanIntentExtras.SCAN_MODE, ScanMode.L1_IMPORT_TRANSPORT.name))
                        },
                    ),
                )
            }
        }
    }
}
