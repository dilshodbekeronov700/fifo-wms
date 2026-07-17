package com.example.pm84scanner

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.Layers
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.ViewModule
import com.example.pm84scanner.ui.menu.MenuItem
import com.example.pm84scanner.ui.menu.MenuScreen
import com.example.pm84scanner.ui.theme.FlowProduction
import com.example.pm84scanner.ui.theme.Pm84Theme

class ProductionMenuActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Pm84Theme {
                MenuScreen(
                    title = "Ishlab chiqarish",
                    accent = FlowProduction,
                    onBack = { finish() },
                    items = listOf(
                        MenuItem("Unit Utilisation", "Faqat dona (010)", Icons.Filled.ViewModule, FlowProduction) {
                            startMain(ScanMode.PRODUCTION_UNIT_ONLY)
                        },
                        MenuItem("L1 — Box Unit", "Quti + birliklar", Icons.Filled.Inventory, FlowProduction) {
                            startMain(ScanMode.L1_BOX_UNIT)
                        },
                        MenuItem("L2 — Transport", "Latok / Paddon / Transport", Icons.Filled.Layers, FlowProduction) {
                            startMain(ScanMode.L2_THREE_TIER)
                        },
                        MenuItem("L3 — Transport zanjiri", "Transport → child kodlar", Icons.Filled.LocalShipping, FlowProduction) {
                            startMain(ScanMode.L3_TRANSPORT_CHAIN)
                        },
                    ),
                )
            }
        }
    }

    private fun startMain(mode: ScanMode) {
        startActivity(Intent(this, MainActivity::class.java).putExtra(ScanIntentExtras.SCAN_MODE, mode.name))
    }
}
