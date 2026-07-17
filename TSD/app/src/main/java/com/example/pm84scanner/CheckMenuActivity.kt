package com.example.pm84scanner

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Widgets
import com.example.pm84scanner.ui.menu.MenuItem
import com.example.pm84scanner.ui.menu.MenuScreen
import com.example.pm84scanner.ui.theme.FlowCheck
import com.example.pm84scanner.ui.theme.Pm84Theme

class CheckMenuActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Pm84Theme {
                MenuScreen(
                    title = "Tekshiruv",
                    accent = FlowCheck,
                    onBack = { finish() },
                    items = listOf(
                        MenuItem("Unit (dona)", null, Icons.Filled.Widgets, FlowCheck) { startCheck(CheckKind.UNIT) },
                        MenuItem("Box (quti)", null, Icons.Filled.Inventory, FlowCheck) { startCheck(CheckKind.BOX) },
                        MenuItem("Transport", null, Icons.Filled.LocalShipping, FlowCheck) { startCheck(CheckKind.TRANSPORT) },
                    ),
                )
            }
        }
    }

    private fun startCheck(kind: CheckKind) {
        startActivity(Intent(this, CheckSingleActivity::class.java).putExtra(ScanIntentExtras.CHECK_KIND, kind.name))
    }
}
