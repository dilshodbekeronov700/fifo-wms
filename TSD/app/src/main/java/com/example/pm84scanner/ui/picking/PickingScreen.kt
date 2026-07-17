package com.example.pm84scanner.ui.picking

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.ShoppingCartCheckout
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.pm84scanner.ui.components.BigButton
import com.example.pm84scanner.ui.components.EmptyState
import com.example.pm84scanner.ui.components.ScreenScaffold
import com.example.pm84scanner.ui.components.StatusChip
import com.example.pm84scanner.ui.theme.Color_White
import com.example.pm84scanner.ui.theme.FlowPicking
import com.example.pm84scanner.ui.theme.Ok

data class UiOrder(val dealId: String, val number: String, val status: String)

@Composable
fun PickingScreen(
    orders: List<UiOrder>,
    statusText: String,
    loading: Boolean,
    confirm: Pair<String, String>?,   // docId to label
    onRefresh: () -> Unit,
    onSelect: (UiOrder) -> Unit,
    onConfirm: (String) -> Unit,
    onBack: () -> Unit,
) {
    ScreenScaffold(
        title = "Terish / Otgruzka",
        subtitle = statusText.ifBlank { null },
        accent = FlowPicking,
        onBack = onBack,
        actions = {
            FilledIconButton(
                onClick = onRefresh,
                colors = IconButtonDefaults.filledIconButtonColors(
                    containerColor = Color_White.copy(alpha = 0.18f), contentColor = Color_White,
                ),
            ) { Icon(Icons.Filled.Refresh, contentDescription = "Yangilash") }
        },
    ) { pad ->
        Box(Modifier.fillMaxSize().padding(pad)) {
            when {
                confirm != null -> Column(
                    Modifier.fillMaxSize().padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(Icons.Filled.ShoppingCartCheckout, contentDescription = null,
                        modifier = Modifier.size(64.dp), tint = Ok)
                    Spacer(Modifier.height(16.dp))
                    Text(confirm.second, style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurface)
                    Text("Reja tayyor — terib bo'lgach yakunlang", style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(24.dp))
                    BigButton("Yakunlash (otgruzka)", onClick = { onConfirm(confirm.first) },
                        container = Ok, modifier = Modifier.fillMaxWidth())
                }
                loading && orders.isEmpty() ->
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
                orders.isEmpty() ->
                    EmptyState(Icons.Filled.ShoppingCartCheckout, "Terishga tayyor buyurtma yo'q")
                else -> LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    items(orders, key = { it.dealId }) { o ->
                        Surface(
                            onClick = { onSelect(o) },
                            shape = RoundedCornerShape(16.dp),
                            color = MaterialTheme.colorScheme.surface,
                            shadowElevation = 2.dp,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                                Text("№ ${o.number.ifBlank { o.dealId }}",
                                    style = MaterialTheme.typography.titleMedium,
                                    color = MaterialTheme.colorScheme.onSurface,
                                    modifier = Modifier.weight(1f))
                                StatusChip(o.status, FlowPicking)
                            }
                        }
                    }
                }
            }
        }
    }
}
