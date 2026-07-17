package com.example.pm84scanner.ui.putaway

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.pm84scanner.ui.components.BigButton
import com.example.pm84scanner.ui.components.ScreenScaffold
import com.example.pm84scanner.ui.theme.*

enum class PutawayPhase { SCAN, SUGGEST, CONFIRM }

data class PutawayCandidate(
    val rank: Int,
    val code: String,
    val zone: String,
    val reason: String,
    val score: Int,
    val locationId: String,
)

@Composable
fun PutawayScreen(
    phase: PutawayPhase,
    hint: String,
    scannedCode: String,
    product: String,
    loading: Boolean,
    candidates: List<PutawayCandidate>,
    qtyOptions: List<Int>,
    selectedQty: Int,
    reservedLocation: String?,
    onSelectQty: (Int) -> Unit,
    onReserve: (String) -> Unit,
    onManualSearch: () -> Unit,
    onCancelReservation: () -> Unit,
    onReset: () -> Unit,
    onBack: () -> Unit,
) {
    ScreenScaffold(
        title = "WMS Joylash",
        subtitle = hint.ifBlank { null },
        accent = FlowPutaway,
        onBack = onBack,
        bottomBar = {
            if (phase != PutawayPhase.SCAN) {
                Surface(shadowElevation = 10.dp, color = MaterialTheme.colorScheme.surface) {
                    Row(Modifier.fillMaxWidth().navigationBarsPadding().padding(16.dp)) {
                        OutlinedButton(
                            onClick = onReset,
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.fillMaxWidth().height(52.dp),
                        ) { Text("Boshidan (reset)", style = MaterialTheme.typography.labelLarge) }
                    }
                }
            }
        },
    ) { pad ->
        Column(Modifier.fillMaxSize().padding(pad)) {
            if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())

            // Skanlangan kod + mahsulot
            if (scannedCode.isNotBlank() || product.isNotBlank()) {
                Surface(
                    color = FlowPutaway.copy(alpha = 0.08f),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        if (product.isNotBlank()) {
                            Text(product, style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onSurface)
                            Spacer(Modifier.height(4.dp))
                        }
                        if (scannedCode.isNotBlank()) {
                            Text(scannedCode, fontFamily = FontFamily.Monospace,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            when (phase) {
                PutawayPhase.SCAN -> ScanPrompt("Transport kodini skanlang", "00… (SSCC) yoki box kodi")
                PutawayPhase.CONFIRM -> ConfirmPrompt(reservedLocation, onCancelReservation)
                PutawayPhase.SUGGEST -> SuggestList(
                    candidates, qtyOptions, selectedQty, onSelectQty, onReserve, onManualSearch,
                )
            }
        }
    }
}

@Composable
private fun ScanPrompt(title: String, sub: String) {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(Icons.Filled.QrCodeScanner, contentDescription = null,
            modifier = Modifier.size(72.dp), tint = FlowPutaway)
        Spacer(Modifier.height(16.dp))
        Text(title, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onSurface)
        Text(sub, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ConfirmPrompt(location: String?, onCancel: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(Icons.Filled.MyLocation, contentDescription = null,
            modifier = Modifier.size(72.dp), tint = Ok)
        Spacer(Modifier.height(16.dp))
        Text("Bron qilindi ✓", style = MaterialTheme.typography.titleLarge, color = Ok)
        Spacer(Modifier.height(8.dp))
        Text("Tavsiya: ${location ?: "?"}", style = MaterialTheme.typography.headlineSmall,
            fontFamily = FontFamily.Monospace, color = MaterialTheme.colorScheme.onSurface)
        Spacer(Modifier.height(8.dp))
        Text("Istalgan bo'sh yacheyka QR/kodini skanlang — shunga joylanadi\n(tavsiya shart emas)",
            style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(24.dp))
        OutlinedButton(onClick = onCancel, shape = RoundedCornerShape(16.dp)) {
            Text("Bronni bekor qilish")
        }
    }
}

@Composable
private fun SuggestList(
    candidates: List<PutawayCandidate>,
    qtyOptions: List<Int>,
    selectedQty: Int,
    onSelectQty: (Int) -> Unit,
    onReserve: (String) -> Unit,
    onManualSearch: () -> Unit,
) {
    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (qtyOptions.size > 1) {
            item {
                Column {
                    Text("Nechta box shu yacheykaga?", style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(6.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        qtyOptions.forEach { opt ->
                            val sel = opt == selectedQty
                            FilterChip(
                                selected = sel,
                                onClick = { onSelectQty(opt) },
                                label = { Text(if (opt == qtyOptions.last()) "Hammasi ($opt)" else "$opt") },
                            )
                        }
                    }
                }
            }
        }
        item {
            Text(
                "Tavsiyadan birini bron qiling — yoki bron qilib, ISTALGAN bo'sh yacheyka " +
                "QR/kodini skanlang, o'shanga joylanadi.",
                style = MaterialTheme.typography.labelMedium,
                color = InkSoft,
                modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp),
            )
        }
        if (candidates.isEmpty()) {
            item { Text("Tavsiya yo'q — bron qilib istalgan yacheykani skanlang", color = InkSoft, modifier = Modifier.padding(8.dp)) }
        }
        items(candidates, key = { it.locationId }) { c -> CandidateCard(c, onReserve) }
    }
}

@Composable
private fun CandidateCard(c: PutawayCandidate, onReserve: (String) -> Unit) {
    val top = c.rank == 1
    val bg by animateColorAsState(
        if (top) FlowPutaway.copy(alpha = 0.10f) else MaterialTheme.colorScheme.surface,
        label = "bg",
    )
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = bg,
        shadowElevation = if (top) 4.dp else 1.dp,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier.size(32.dp).clip(RoundedCornerShape(10.dp))
                        .background(if (top) FlowPutaway else InkSoft.copy(alpha = 0.25f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("${c.rank}", color = Color_White, fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.labelMedium)
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(c.code, style = MaterialTheme.typography.titleMedium,
                        fontFamily = FontFamily.Monospace, color = MaterialTheme.colorScheme.onSurface)
                    Text(c.zone, style = MaterialTheme.typography.labelMedium, color = InkSoft)
                }
                Text("${c.score}", style = MaterialTheme.typography.headlineSmall, color = FlowPutaway)
            }
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { (c.score.coerceIn(0, 100)) / 100f },
                modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)),
                color = FlowPutaway,
            )
            Spacer(Modifier.height(8.dp))
            Text(c.reason, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(10.dp))
            BigButton("Bron qilish", onClick = { onReserve(c.locationId) },
                container = FlowPutaway, modifier = Modifier.fillMaxWidth())
        }
    }
}
