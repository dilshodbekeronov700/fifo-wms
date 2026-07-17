package com.example.pm84scanner

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import java.nio.charset.Charset

class DecodeBroadcastReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        val action = intent?.action ?: return
        if (!SUPPORTED_ACTIONS.contains(action)) return

        try {
            val extras = intent.extras
            if (extras != null) {
                val sb = StringBuilder()
                sb.append("action=").append(intent.action).append(" keys=").append(extras.keySet().size)
                for (k in extras.keySet()) {
                    val v = extras.get(k)
                    val display = when (v) {
                        is ByteArray -> "byte[${v.size}]"
                        else -> v?.toString() ?: "null"
                    }
                    sb.append("\n- ").append(k).append(" = ").append(display)
                }
                Log.d("PM84_SCAN_EVENT_BG", sb.toString())
            }
        } catch (_: Throwable) {
            // ignore
        }

        val rawBytes = intent.getByteArrayExtra(EXTRA_DATA)
        val barcodeData = if (rawBytes != null && rawBytes.isNotEmpty()) {
            try {
                String(rawBytes, Charsets.UTF_8)
            } catch (_: Exception) {
                String(rawBytes, Charset.defaultCharset())
            }
        } else {
            intent.getStringExtra(EXTRA_DATA).orEmpty()
        }
        val barcodeType = intent.getStringExtra(EXTRA_TYPE).orEmpty()
        Log.d("DecodeBroadcastReceiver", "Received decode: type=$barcodeType, data=$barcodeData")
    }

    companion object {
        const val ACTION_DECODE = "device.scanner.EVENT"
        const val ACTION_DECODE_PM = "com.pointmobile.pda.samples.decode"
        const val EXTRA_DATA = "EXTRA_EVENT_DECODE_STRING_VALUE"
        const val EXTRA_TYPE = "EXTRA_EVENT_DECODE_TYPE"
        val SUPPORTED_ACTIONS = setOf(ACTION_DECODE, ACTION_DECODE_PM)
    }
}
