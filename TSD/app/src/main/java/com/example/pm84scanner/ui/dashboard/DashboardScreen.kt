package com.example.pm84scanner.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.pm84scanner.ui.theme.*

/** Dashboard amali — Activity'ga route nomi qaytaradi. */
data class DashAction(
    val id: String,
    val label: String,
    val icon: ImageVector,
    val color: Color,
)

private val ACTIONS = listOf(
    DashAction("production", "Ishlab chiqarish", Icons.Filled.Factory, FlowProduction),
    DashAction("check", "Tekshiruv", Icons.Filled.QrCodeScanner, FlowCheck),
    DashAction("import", "Import", Icons.Filled.Download, FlowImport),
    DashAction("putaway", "Joylash", Icons.Filled.Inventory2, FlowPutaway),
    // Kirim (Receipt) hozircha YASHIRILGAN — joylash (putaway) to'g'ridan yacheykaga
    // qabul qiladi, alohida kirim qadami kerak emas. Qaytarish: izohni oching.
    // DashAction("receipt", "Kirim", Icons.Filled.MoveToInbox, FlowReceipt),
    DashAction("picking", "Terish", Icons.Filled.ShoppingCartCheckout, FlowPicking),
    DashAction("inventory", "Inventarizatsiya", Icons.Filled.Checklist, FlowInventory),
    DashAction("tasks", "Vazifalar", Icons.Filled.AssignmentTurnedIn, FlowTasks),
)

sealed class SyncState(val text: String) {
    data class Online(val n: Int = 0) : SyncState(if (n == 0) "Online · sinxron" else "Yuborilmoqda…")
    data class Offline(val n: Int) : SyncState(if (n == 0) "Offline rejim" else "Navbatda: $n operatsiya")
}

@Composable
fun DashboardScreen(
    sync: SyncState,
    warehouseName: String?,
    onAction: (String) -> Unit,
    onSettings: () -> Unit,
) {
    Scaffold(containerColor = MaterialTheme.colorScheme.background) { pad ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(pad)
        ) {
            DashHeader(sync, warehouseName, onSettings)
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                contentPadding = PaddingValues(16.dp),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
                modifier = Modifier.fillMaxSize(),
            ) {
                items(ACTIONS, key = { it.id }) { a ->
                    ActionCard(a) { onAction(a.id) }
                }
            }
        }
    }
}

@Composable
private fun DashHeader(sync: SyncState, warehouseName: String?, onSettings: () -> Unit) {
    Box(
        Modifier
            .fillMaxWidth()
            .background(
                Brush.linearGradient(listOf(BrandIndigoDark, BrandIndigo, BrandIndigoLight))
            )
            .padding(20.dp)
            .padding(top = 12.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("PM84 · WMS", style = MaterialTheme.typography.displaySmall, color = Color_White)
                    Text(
                        warehouseName ?: "Sklad terminali",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color_White.copy(alpha = 0.85f),
                    )
                }
                FilledIconButton(
                    onClick = onSettings,
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = Color_White.copy(alpha = 0.18f),
                        contentColor = Color_White,
                    ),
                ) { Icon(Icons.Filled.Settings, contentDescription = "Sozlamalar") }
            }
            Spacer(Modifier.height(16.dp))
            SyncPill(sync)
        }
    }
}

@Composable
private fun SyncPill(sync: SyncState) {
    val (dot, label) = when (sync) {
        is SyncState.Online -> Ok to sync.text
        is SyncState.Offline -> (if (sync.n > 0) Warn else InkSoft) to sync.text
    }
    Row(
        Modifier
            .clip(CircleShape)
            .background(Color_White.copy(alpha = 0.16f))
            .padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(dot)
        )
        Spacer(Modifier.width(8.dp))
        Text(label, style = MaterialTheme.typography.labelLarge, color = Color_White)
    }
}

@Composable
private fun ActionCard(a: DashAction, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 3.dp,
        modifier = Modifier
            .fillMaxWidth()
            .height(132.dp),
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Box(
                Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(
                        Brush.linearGradient(listOf(a.color, a.color.copy(alpha = 0.72f)))
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(a.icon, contentDescription = a.label, tint = Color_White, modifier = Modifier.size(28.dp))
            }
            Text(
                a.label,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}
