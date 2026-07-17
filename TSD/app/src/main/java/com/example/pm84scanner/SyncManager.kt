package com.example.pm84scanner

import android.content.Context
import android.util.Log
import kotlin.concurrent.thread

/**
 * Replays the offline queue against the WMS backend when connectivity is back
 * (TZ §8). Builds the client from SharedPreferences; refreshes the token via
 * re-login on 401. Safe to call from any screen's onResume.
 */
object SyncManager {

    @Volatile private var running = false

    fun syncAsync(context: Context, onDone: ((Int) -> Unit)? = null) {
        if (running) return
        if (!ConnectivityHelper.isOnline(context)) return
        running = true
        val appCtx = context.applicationContext
        thread(name = "wms-sync") {
            val flushed = try {
                flush(appCtx)
            } catch (e: Exception) {
                Log.e(TAG, "sync error: ${e.message}"); 0
            } finally {
                running = false
            }
            onDone?.invoke(flushed)
        }
    }

    private fun flush(context: Context): Int {
        val prefs = context.getSharedPreferences(WmsApiClient.PREFS, Context.MODE_PRIVATE)
        val baseUrl = prefs.getString(WmsApiClient.KEY_WMS_URL, null) ?: return 0
        var token = prefs.getString(WmsApiClient.KEY_WMS_TOKEN, "").orEmpty()
        val client = WmsApiClient(baseUrl, token)
        val queue = OfflineQueue(context)

        var flushed = 0
        for (op in queue.all()) {
            var res = client.postJson(op.path, op.payload)

            // Token expired → try a single re-login with stored credentials.
            if (res.code == 401) {
                val email = prefs.getString(WmsApiClient.KEY_WMS_EMAIL, null)
                val pass = prefs.getString(WmsApiClient.KEY_WMS_PASSWORD, null)
                if (!email.isNullOrBlank() && !pass.isNullOrBlank()) {
                    val newToken = client.login(email, pass)
                    if (newToken != null) {
                        token = newToken
                        prefs.edit().putString(WmsApiClient.KEY_WMS_TOKEN, newToken).apply()
                        client.setToken(newToken)
                        res = client.postJson(op.path, op.payload)
                    }
                }
            }

            when {
                res.ok -> { queue.remove(op.id); flushed++ }
                res.code in 400..499 && res.code != 401 && res.code != 429 -> {
                    // Permanent client error (validation) — drop to avoid an infinite loop.
                    Log.w(TAG, "Dropping op ${op.id} (${op.type}) after ${res.code}: ${res.body}")
                    queue.remove(op.id)
                }
                else -> {
                    queue.bumpAttempts(op.id)
                    if (op.attempts + 1 >= OfflineQueue.MAX_ATTEMPTS) {
                        Log.e(TAG, "Op ${op.id} exceeded max attempts — dropping")
                        queue.remove(op.id)
                    }
                }
            }
        }
        if (flushed > 0) Log.i(TAG, "Synced $flushed offline operation(s)")
        return flushed
    }

    private const val TAG = "SyncManager"
}
