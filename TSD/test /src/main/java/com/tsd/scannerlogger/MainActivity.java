package com.tsd.scannerlogger;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {

    private EditText etScanResult;
    private TextView tvLog;
    private ScrollView scrollView;
    private final StringBuilder logBuilder = new StringBuilder();
    private final StringBuilder keyBuffer = new StringBuilder();
    private BroadcastReceiver scanReceiver;

    private static final String[] SCANNER_ACTIONS = {
            "com.pointmobile.scanner.ACTION_DECODE",
            "device.scanner.ACTION_BARCODE_FOUND",
            "com.symbol.datawedge.api.ACTION",
            "com.motorolasolutions.emdk.action.DATA_RETURN_TYPE_LABEL_TYPE",
            "unitech.scanservice.data",
            "android.intent.action.MAIN",
            "scan.rcv.message",
            "com.android.server.scannerservice.broadcast",
            "ACTION_BARCODE_DATA",
            "nlscan.action.SCANNER_RESULT",
            "com.honeywell.decode.intent.action.EDIT_DATA",
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        etScanResult = new EditText(this);
        etScanResult.setHint("Scan natijasi shu yerga tushadi");
        etScanResult.setInputType(InputType.TYPE_CLASS_TEXT);
        etScanResult.setSingleLine(true);
        root.addView(etScanResult, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        scrollView = new ScrollView(this);
        tvLog = new TextView(this);
        tvLog.setTextSize(13);
        tvLog.setPadding(16, 16, 16, 16);
        tvLog.setTextColor(0xFF00FF00);
        tvLog.setBackgroundColor(0xFF000000);
        tvLog.setTypeface(android.graphics.Typeface.MONOSPACE);
        scrollView.addView(tvLog);
        root.addView(scrollView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1f
        ));
        setContentView(root);

        appendLog("=== PM84 Scanner Logger ===");
        appendLog("Scan qiling, action ko'rsatiladi...\n");

        registerScannerReceivers();
    }

    private void registerScannerReceivers() {
        scanReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String action = intent.getAction();
                appendLog("ACTION: " + action);

                Bundle extras = intent.getExtras();
                String scanData = extractScanData(extras);
                if (!scanData.isEmpty()) {
                    etScanResult.setText(scanData);
                    etScanResult.setSelection(scanData.length());
                    appendLog("SCAN: " + scanData);
                }
                if (extras != null) {
                    for (String key : extras.keySet()) {
                        Object value = extras.get(key);
                        appendLog("   KEY: " + key);
                        appendLog("   VAL: " + (value != null ? value.toString() : "null"));
                    }
                } else {
                    appendLog("   (extras yo'q)");
                }
                appendLog("---");
            }
        };

        IntentFilter filter = new IntentFilter();
        for (String action : SCANNER_ACTIONS) {
            filter.addAction(action);
        }

        try {
            registerReceiver(scanReceiver, filter);
            appendLog("Receiver ro'yxatdan o'tdi (" + SCANNER_ACTIONS.length + " action)\n");
        } catch (Exception e) {
            appendLog("Xato: " + e.getMessage());
        }
    }

    private String extractScanData(Bundle extras) {
        if (extras == null) {
            return "";
        }
        String[] preferredKeys = {
                "data",
                "DATA",
                "decoded_data",
                "barcodeData",
                "barcode_string",
                "SCAN_BARCODE1",
                "com.symbol.datawedge.data_string"
        };

        for (String key : preferredKeys) {
            Object value = extras.get(key);
            if (value instanceof String && !((String) value).isEmpty()) {
                return (String) value;
            }
        }

        for (String key : extras.keySet()) {
            Object value = extras.get(key);
            if (value instanceof String && !((String) value).isEmpty()) {
                return (String) value;
            }
        }
        return "";
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            int keyCode = event.getKeyCode();
            if (keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_TAB) {
                commitBufferedScan();
                return true;
            }

            char c = (char) event.getUnicodeChar();
            if (c >= 32 && c <= 126) {
                keyBuffer.append(c);
                return true;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private void commitBufferedScan() {
        if (keyBuffer.length() == 0) {
            return;
        }
        String scanData = keyBuffer.toString();
        keyBuffer.setLength(0);
        etScanResult.setText(scanData);
        etScanResult.setSelection(scanData.length());
        appendLog("KEYEVENT SCAN: " + scanData);
    }

    private void appendLog(String text) {
        String time = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
        logBuilder.append("[").append(time).append("] ").append(text).append("\n");
        tvLog.setText(logBuilder.toString());
        scrollView.post(() -> scrollView.fullScroll(ScrollView.FOCUS_DOWN));
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (scanReceiver != null) {
            try {
                unregisterReceiver(scanReceiver);
            } catch (Exception ignored) {
            }
        }
    }
}
