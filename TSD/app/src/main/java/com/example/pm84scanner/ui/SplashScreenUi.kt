package com.example.pm84scanner.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warehouse
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.unit.dp
import com.example.pm84scanner.ui.theme.BrandIndigo
import com.example.pm84scanner.ui.theme.BrandIndigoDark
import com.example.pm84scanner.ui.theme.BrandIndigoLight
import com.example.pm84scanner.ui.theme.Color_White

@Composable
fun SplashScreenUi() {
    Box(
        Modifier
            .fillMaxSize()
            .background(Brush.linearGradient(listOf(BrandIndigoDark, BrandIndigo, BrandIndigoLight))),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                Modifier.size(96.dp).clip(RoundedCornerShape(28.dp)).background(Color_White.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center,
            ) { Icon(Icons.Filled.Warehouse, contentDescription = null, tint = Color_White, modifier = Modifier.size(52.dp)) }
            Spacer(Modifier.height(20.dp))
            Text("PM84 · WMS", style = MaterialTheme.typography.displaySmall, color = Color_White)
            Text("Sklad terminali", style = MaterialTheme.typography.bodyLarge, color = Color_White.copy(alpha = 0.85f))
            Spacer(Modifier.height(28.dp))
            CircularProgressIndicator(color = Color_White, strokeWidth = 3.dp, modifier = Modifier.size(28.dp))
        }
    }
}
