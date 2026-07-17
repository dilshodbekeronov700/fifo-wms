package com.example.pm84scanner.ui.check

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.example.pm84scanner.ui.components.BigButton
import com.example.pm84scanner.ui.components.ScreenScaffold
import com.example.pm84scanner.ui.components.StatusChip
import com.example.pm84scanner.ui.theme.FlowCheck
import com.example.pm84scanner.ui.theme.InkSoft
import com.example.pm84scanner.ui.theme.Ok

data class UiTreeRow(val code: String, val status: String, val depth: Int, val detail: String)

@Composable
fun CheckScreen(
    hint: String,
    buffer: List<String>,
    rows: List<UiTreeRow>,
    loading: Boolean,
    onSend: () -> Unit,
    onClear: () -> Unit,
    onBack: () -> Unit,
) {
    ScreenScaffold(
        title = "Tekshiruv (COD)",
        subtitle = hint.ifBlank { null },
        accent = FlowCheck,
        onBack = onBack,
        bottomBar = {
            Surface(shadowElevation = 10.dp, color = MaterialTheme.colorScheme.surface) {
                Row(
                    Modifier.fillMaxWidth().navigationBarsPadding().padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    OutlinedButton(
                        onClick = onClear,
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.weight(1f).height(56.dp),
                    ) { Text("Tozalash", style = MaterialTheme.typography.labelLarge) }
                    BigButton(
                        text = "Tekshirish (${buffer.size})",
                        onClick = onSend,
                        enabled = buffer.isNotEmpty() && !loading,
                        container = FlowCheck,
                        modifier = Modifier.weight(1.4f),
                    )
                }
            }
        },
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad)) {
            if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())

            // Skanlangan kodlar buferi
            if (buffer.isNotEmpty()) {
                Surface(color = FlowCheck.copy(alpha = 0.08f), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Skanlangan: ${buffer.size}", style = MaterialTheme.typography.labelMedium, color = InkSoft)
                        Spacer(Modifier.height(4.dp))
                        buffer.takeLast(6).forEach {
                            Text(it, fontFamily = FontFamily.Monospace, style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface)
                        }
                    }
                }
            }

            when {
                rows.isEmpty() && !loading -> Column(
                    Modifier.fillMaxSize().padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(Icons.Filled.QrCodeScanner, contentDescription = null,
                        modifier = Modifier.size(64.dp), tint = FlowCheck)
                    Spacer(Modifier.height(12.dp))
                    Text("Kod skanlang, keyin «Tekshirish»", color = InkSoft,
                        style = MaterialTheme.typography.bodyLarge)
                }
                else -> LazyColumn(
                    contentPadding = PaddingValues(12.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    itemsIndexed(rows) { i, r -> TreeRowCard(r) }
                }
            }
        }
    }
}

@Composable
private fun TreeRowCard(r: UiTreeRow) {
    var expanded by remember { mutableStateOf(false) }
    Surface(
        onClick = { expanded = !expanded },
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 1.dp,
        modifier = Modifier.fillMaxWidth().padding(start = (r.depth * 16).dp),
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(6.dp).clip(RoundedCornerShape(3.dp))
                    .background(if (r.depth == 0) FlowCheck else InkSoft))
                Spacer(Modifier.width(10.dp))
                Text(r.code, fontFamily = FontFamily.Monospace, style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface, modifier = Modifier.weight(1f))
                StatusChip(r.status, if (r.status == "—") InkSoft else Ok)
            }
            AnimatedVisibility(expanded) {
                Text(
                    r.detail,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 8.dp, start = 16.dp),
                )
            }
        }
    }
}
