/**
 * In-app PDF/document preview. The document streams from the server through an
 * in-app WebView-backed viewer.
 *
 * Because expo-managed doesn't ship a native PDF component out of the box, we
 * use Google's Docs Viewer as a robust viewer (works for PDF/DOC/DOCX/XLS/
 * PPT/TXT). Sharing hands the file to the OS viewer with an on-demand download
 * when the user asks for it — the app is online-only (no offline media cache).
 */
import React, { useEffect, useMemo, useState } from "react";
import { View, Pressable, StyleSheet, StatusBar, Platform, ActivityIndicator, Linking } from "react-native";
import { Stack, useLocalSearchParams, router } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import * as Sharing from "expo-sharing";
import { Ionicons } from "@expo/vector-icons";
import { AppText, Button } from "@/src/ui";
import { useTheme, spacing } from "@/src/theme";
import { track } from "@/src/analytics";

export default function PdfViewer() {
  const { colors } = useTheme();
  const params = useLocalSearchParams<{ uri: string; cacheKey?: string; title?: string; ext?: string; mime?: string }>();
  const [localUri, setLocalUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const remote = String(params.uri || "");
  const title = String(params.title || "Document");

  useEffect(() => {
    track("media_viewed_pdf", { ext: String(params.ext || "") });
    // Online-only: preview streams via the in-app browser viewer; the share
    // action downloads on demand (no offline media cache).
    setLoading(false);
  }, [remote, params.ext]);

  // We can only hand a public URL to Google Docs Viewer. Our storage requires a
  // signed token in the URL, and that token is already embedded in `remote`.
  const googleViewer = useMemo(() => {
    if (!remote) return null;
    return `https://docs.google.com/gview?embedded=true&url=${encodeURIComponent(remote)}`;
  }, [remote]);

  const openInApp = async () => {
    try {
      if (googleViewer) {
        await WebBrowser.openBrowserAsync(googleViewer, {
          controlsColor: colors.brandPrimary,
          toolbarColor: "#0b0b12",
          enableBarCollapsing: true,
          dismissButtonStyle: "close",
        });
        return;
      }
    } catch {}
    // fallback: try local sharing (offline)
    try {
      if (localUri && await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(localUri);
        return;
      }
    } catch {}
    try { await Linking.openURL(remote); } catch {}
  };

  const openLocalWithOs = async () => {
    // Download on demand (user-initiated), then hand off to the OS.
    try {
      let target = localUri;
      if (!target && remote) {
        const FS: any = require("expo-file-system/legacy");
        const ext = String(params.ext || ".pdf");
        target = (FS.cacheDirectory || "") + "share-" + Date.now() + ext;
        const r = await FS.downloadAsync(remote, target);
        target = r?.uri || target;
        setLocalUri(target);
      }
      if (target && await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(target, { mimeType: String(params.mime || "application/pdf"), dialogTitle: title });
      }
    } catch {
      setError("Couldn't download this document. Check your connection and try again.");
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: "#0b0b12" }}>
      <Stack.Screen options={{ headerShown: false }} />
      <StatusBar barStyle="light-content" backgroundColor="#0b0b12" />
      <View style={styles.header}>
        <Pressable testID="pdf-viewer-close" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="close" size={26} color="#fff" />
        </Pressable>
        <AppText color="#fff" weight="semibold" numberOfLines={1} style={{ flex: 1, marginLeft: 12 }}>{title}</AppText>
        {localUri ? (
          <Pressable testID="pdf-viewer-share" onPress={openLocalWithOs} hitSlop={12} style={styles.iconBtn}>
            <Ionicons name="share-outline" size={22} color="#fff" />
          </Pressable>
        ) : null}
      </View>
      <View style={{ flex: 1, padding: spacing.lg, alignItems: "center", justifyContent: "center" }}>
        <Ionicons name="document-text-outline" size={72} color="#e5e7eb" />
        <AppText color="#fff" weight="bold" size="xl" style={{ marginTop: spacing.md }}>{title}</AppText>
        <AppText color="#a1a1aa" style={{ marginTop: 8, textAlign: "center" }}>
          {loading ? "Downloading document…" : error ? error : "Preview this document inside Chatly."}
        </AppText>
        {loading ? (
          <ActivityIndicator color="#fff" style={{ marginTop: spacing.lg }} />
        ) : (
          <View style={{ marginTop: spacing.xl, width: "100%", gap: 12 }}>
            <Button testID="pdf-viewer-open" title="Preview in Chatly" onPress={openInApp} />
            {localUri ? (
              <Button testID="pdf-viewer-open-os" title="Open with another app" variant="secondary" onPress={openLocalWithOs} />
            ) : null}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    height: Platform.OS === "ios" ? 88 : 56,
    paddingTop: Platform.OS === "ios" ? 44 : 8,
    paddingHorizontal: 12,
    flexDirection: "row", alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  iconBtn: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
});
