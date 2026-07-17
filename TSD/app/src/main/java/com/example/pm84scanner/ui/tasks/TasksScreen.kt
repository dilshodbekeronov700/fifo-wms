package com.example.pm84scanner.ui.tasks

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AssignmentTurnedIn
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.pm84scanner.ui.components.EmptyState
import com.example.pm84scanner.ui.components.ScreenScaffold
import com.example.pm84scanner.ui.components.StatusChip
import com.example.pm84scanner.ui.theme.*

data class UiTask(
    val id: String,
    val type: String,
    val status: String,
    val priority: Int,
    val detail: String,
)

private val TYPE_LABEL = mapOf(
    "putaway" to "Joylash", "pick" to "Terish", "replenish" to "To'ldirish",
    "count" to "Inventarizatsiya", "move" to "Ko'chirish",
)
private val STATUS_LABEL = mapOf(
    "pending" to "Kutmoqda", "assigned" to "Tayinlangan", "in_progress" to "Jarayonda",
    "completed" to "Tugallangan", "cancelled" to "Bekor",
)
private fun statusColor(s: String): Color = when (s) {
    "pending" -> Warn
    "assigned", "in_progress" -> FlowPutaway
    "completed" -> Ok
    "cancelled" -> Danger
    else -> InkSoft
}

@Composable
fun TasksScreen(
    tasks: List<UiTask>,
    syncLabel: String,
    loading: Boolean,
    onBack: () -> Unit,
) {
    ScreenScaffold(title = "Vazifalar", subtitle = syncLabel, accent = FlowTasks, onBack = onBack) { pad ->
        when {
            loading && tasks.isEmpty() ->
                Box(Modifier.fillMaxSize().padding(pad), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            tasks.isEmpty() ->
                EmptyState(Icons.Filled.AssignmentTurnedIn, "Hozircha vazifa yo'q", Modifier.padding(pad))
            else -> LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.padding(pad),
            ) {
                items(tasks, key = { it.id }) { TaskCard(it) }
            }
        }
    }
}

@Composable
private fun TaskCard(t: UiTask) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    TYPE_LABEL[t.type] ?: t.type.uppercase(),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f),
                )
                StatusChip(STATUS_LABEL[t.status] ?: t.status, statusColor(t.status))
            }
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "P${t.priority}",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    t.detail,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
