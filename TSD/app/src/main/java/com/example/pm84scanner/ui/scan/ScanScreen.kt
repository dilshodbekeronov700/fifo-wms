package com.example.pm84scanner.ui.scan

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.example.pm84scanner.ui.components.BigButton
import com.example.pm84scanner.ui.components.ScreenScaffold
import com.example.pm84scanner.ui.theme.InkSoft

data class LogLine(val text: String, val color: Long)

/** Barcha skan-ekranlari uchun umumiy ko'rinish: sarlavha + hisoblagich + log + 2 tugma. */
@Composable
fun ScanScreen(
    title: String,
    hint: String,
    accent: Color,
    counter: String,
    log: List<LogLine>,
    primaryLabel: String,
    secondaryLabel: String,
    secondaryVisible: Boolean,
    primaryEnabled: Boolean,
    onPrimary: () -> Unit,
    onSecondary: () -> Unit,
    onBack: () -> Unit,
) {
    ScreenScaffold(
        title = title,
        subtitle = hint.ifBlank { null },
        accent = accent,
        onBack = onBack,
        bottomBar = {
            Surface(shadowElevation = 10.dp, color = MaterialTheme.colorScheme.surface) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    if (secondaryVisible) {
                        OutlinedButton(
                            onClick = onSecondary,
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.weight(1f).height(56.dp),
                        ) { Text(secondaryLabel, style = MaterialTheme.typography.labelLarge) }
                    }
                    BigButton(
                        text = primaryLabel,
                        onClick = onPrimary,
                        enabled = primaryEnabled,
                        container = accent,
                        modifier = Modifier.weight(if (secondaryVisible) 1.4f else 1f),
                    )
                }
            }
        },
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad)) {
            // Hisoblagich + skan ishorasi
            Row(
                Modifier.fillMaxWidth().padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Filled.QrCodeScanner, contentDescription = null, tint = accent)
                Spacer(Modifier.width(10.dp))
                Text(
                    counter.ifBlank { "Skanlashga tayyor" },
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }
            HorizontalDivider()
            if (log.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Kod skanlang…", color = InkSoft, style = MaterialTheme.typography.bodyLarge)
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    itemsIndexed(log) { _, line ->
                        Text(
                            line.text,
                            color = Color(line.color),
                            fontFamily = if (line.text.any { it.isDigit() }) FontFamily.Monospace else FontFamily.Default,
                            style = MaterialTheme.typography.bodyLarge,
                        )
                    }
                }
            }
        }
    }
}
