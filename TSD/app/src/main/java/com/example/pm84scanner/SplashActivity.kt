package com.example.pm84scanner

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.compose.setContent
import androidx.appcompat.app.AppCompatActivity
import com.example.pm84scanner.ui.SplashScreenUi
import com.example.pm84scanner.ui.theme.Pm84Theme

/** Launcher: ~1.75 s logo (Compose), keyin MainDashboardActivity. */
class SplashActivity : AppCompatActivity() {

    private val handler = Handler(Looper.getMainLooper())
    private val goDashboard = Runnable {
        startActivity(Intent(this, MainDashboardActivity::class.java))
        finish()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { Pm84Theme { SplashScreenUi() } }
        handler.postDelayed(goDashboard, SPLASH_MS)
    }

    override fun onDestroy() {
        handler.removeCallbacks(goDashboard)
        super.onDestroy()
    }

    companion object {
        private const val SPLASH_MS = 1750L
    }
}
