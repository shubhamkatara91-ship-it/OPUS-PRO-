package com.opuspro.txi;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.Gravity;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import android.text.InputType;

public class MainActivity extends Activity {
    private static final String PREFS = "opus_pro_settings";
    private static final String KEY_URL = "backend_url";
    private static final String DEFAULT_URL = "https://opus-pro-api.onrender.com";
    private static final int BG = Color.rgb(16, 27, 36);
    private WebView webView;
    private ProgressBar progress;
    private TextView errorView;
    private SharedPreferences prefs;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        root.addView(progress, new LinearLayout.LayoutParams(-1, dp(3)));

        webView = new WebView(this);
        webView.setBackgroundColor(BG);
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setUseWideViewPort(true);
        webView.getSettings().setLoadWithOverviewMode(false);
        webView.setVerticalScrollBarEnabled(true);
        webView.setHorizontalScrollBarEnabled(false);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);
        webView.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        if (android.os.Build.VERSION.SDK_INT >= 26) webView.getSettings().setSafeBrowsingEnabled(true);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int value) {
                progress.setProgress(value);
                progress.setVisibility(value >= 100 ? View.GONE : View.VISIBLE);
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !isAllowedOrigin(request.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return !isAllowedOrigin(Uri.parse(url));
            }
            @Override public void onPageFinished(WebView view, String url) {
                errorView.setVisibility(View.GONE);
                webView.setVisibility(View.VISIBLE);
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, android.webkit.WebResourceError error) {
                if (request.isForMainFrame()) showLoadError();
            }
            @Override public void onReceivedHttpError(WebView view, WebResourceRequest request, android.webkit.WebResourceResponse response) {
                if (request.isForMainFrame() && response.getStatusCode() >= 500) showLoadError();
            }
        });
        root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1));

        errorView = new TextView(this);
        errorView.setTextColor(Color.WHITE);
        errorView.setTextSize(16);
        errorView.setGravity(Gravity.CENTER);
        errorView.setPadding(dp(28), dp(24), dp(28), dp(24));
        errorView.setText("Unable to connect to the OPUS PRO server. Check your internet connection or server URL, then tap to retry.");
        errorView.setOnClickListener(v -> webView.reload());
        errorView.setVisibility(View.GONE);
        root.addView(errorView, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);

        String saved = prefs.getString(KEY_URL, DEFAULT_URL);
        if (saved.isEmpty()) saved = DEFAULT_URL;
        loadApp(saved);
    }

    private int dp(int value) { return (int)(value * getResources().getDisplayMetrics().density); }
    private String getBaseUrl() { return prefs.getString(KEY_URL, ""); }

    private boolean isAllowedOrigin(Uri uri) {
        Uri base = Uri.parse(getBaseUrl());
        return "https".equalsIgnoreCase(uri.getScheme())
            && uri.getHost() != null
            && uri.getHost().equalsIgnoreCase(base.getHost())
            && effectivePort(uri) == effectivePort(base);
    }

    private int effectivePort(Uri uri) { return uri.getPort() == -1 ? 443 : uri.getPort(); }

    private void loadApp(String url) {
        String clean = normalize(url);
        if (clean == null) { showServerDialog(true); return; }
        prefs.edit().putString(KEY_URL, clean).apply();
        errorView.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
        webView.loadUrl(clean + "/");
    }

    private String normalize(String raw) {
        if (raw == null) return null;
        String s = raw.trim().replaceAll("/+$", "");
        Uri uri = Uri.parse(s);
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null) return null;
        if (uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null) return null;
        if (s.contains(" ")) return null;
        return s;
    }

    private void showLoadError() {
        webView.setVisibility(View.GONE);
        errorView.setVisibility(View.VISIBLE);
        progress.setVisibility(View.GONE);
    }

    private void showServerDialog(boolean firstRun) {
        final EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setHint("https://your-opus-server.example.com");
        input.setText(getBaseUrl());
        LinearLayout box = new LinearLayout(this);
        box.setPadding(dp(20), dp(8), dp(20), 0);
        box.addView(input, new LinearLayout.LayoutParams(-1, -2));
        new AlertDialog.Builder(this)
            .setTitle("Connect OPUS PRO server")
            .setMessage("Enter the HTTPS URL where OPUS PRO is deployed. Live results require a working server connection.")
            .setView(box)
            .setCancelable(!firstRun)
            .setPositiveButton("Connect", (dialog, which) -> {
                String url = normalize(input.getText().toString());
                if (url == null) {
                    Toast.makeText(this, "Enter a valid HTTPS server URL", Toast.LENGTH_LONG).show();
                    showServerDialog(true);
                } else loadApp(url);
            })
            .setNegativeButton(firstRun ? "Exit" : "Cancel", (dialog, which) -> { if (firstRun) finish(); })
            .show();
    }

    @Override public boolean onCreateOptionsMenu(Menu menu) {
        menu.add("Change server").setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        menu.add("Refresh").setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        return true;
    }
    @Override public boolean onOptionsItemSelected(MenuItem item) {
        if ("Change server".contentEquals(item.getTitle())) { showServerDialog(false); return true; }
        if ("Refresh".contentEquals(item.getTitle())) { webView.reload(); return true; }
        return super.onOptionsItemSelected(item);
    }
    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }
    @Override protected void onDestroy() {
        if (webView != null) { webView.stopLoading(); webView.destroy(); }
        super.onDestroy();
    }
}
