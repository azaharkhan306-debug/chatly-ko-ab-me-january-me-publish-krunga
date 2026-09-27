import { useState } from "react";
import { View, KeyboardAvoidingView, Platform, ScrollView, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Logo } from "@/src/Logo";
import { useTheme, spacing } from "@/src/theme";
import { AppText, Input, Button, useToast } from "@/src/ui";
import { useAuth } from "@/src/auth";
import { LegalLinks } from "@/src/LegalDoc";

export default function Login() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const toast = useToast();
  const { login, loginWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [err, setErr] = useState("");

  const onGoogle = async () => {
    setGoogleLoading(true); setErr("");
    try { await loginWithGoogle(); router.replace("/(tabs)"); }
    catch (e: any) { if (Platform.OS !== "web") setErr(e.message); }
    finally { setGoogleLoading(false); }
  };

  const onLogin = async () => {
    if (!email.trim() || !password) { setErr("Enter email and password"); return; }
    setErr(""); setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace("/(tabs)");
    } catch (e: any) {
      if (String(e.message).toLowerCase().includes("verify")) {
        toast.show("Please verify your email. Code sent.", "info");
        router.push({ pathname: "/(auth)/verify", params: { email: email.trim() } });
      } else {
        setErr(e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: spacing.xl, paddingTop: insets.top + spacing.xxl, flexGrow: 1 }} keyboardShouldPersistTaps="handled">
          <View style={{ alignItems: "center", marginBottom: spacing.xxl }}>
            <View style={{ marginBottom: spacing.lg }}>
              <Logo size={72} />
            </View>
            <AppText size="xxl" weight="heavy">Chatly AI</AppText>
            <AppText muted style={{ marginTop: 4 }}>Your AI-native messenger</AppText>
          </View>

          <AppText size="xl" weight="bold" style={{ marginBottom: spacing.lg }}>Welcome back</AppText>
          <Input testID="login-email-input" label="Email" icon="mail-outline" value={email} onChangeText={setEmail} placeholder="you@example.com" keyboardType="email-address" />
          <Input testID="login-password-input" label="Password" icon="lock-closed-outline" value={password} onChangeText={setPassword} placeholder="Your password" secureTextEntry error={err} />

          <Pressable testID="forgot-link" onPress={() => router.push("/(auth)/forgot")} style={{ alignSelf: "flex-end", marginBottom: spacing.lg }}>
            <AppText size="sm" weight="semibold" color={colors.brandPrimary}>Forgot password?</AppText>
          </Pressable>

          <Button testID="login-submit-button" title="Log In" onPress={onLogin} loading={loading} />

          <View style={{ flexDirection: "row", alignItems: "center", marginVertical: spacing.lg }}>
            <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
            <AppText muted size="sm" style={{ marginHorizontal: spacing.md }}>or</AppText>
            <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
          </View>

          <Button testID="google-signin-button" title="Continue with Google" variant="secondary" icon="logo-google" onPress={onGoogle} loading={googleLoading} />


          <View style={{ flexDirection: "row", justifyContent: "center", marginTop: spacing.xl }}>
            <AppText muted>Don{"'"}t have an account? </AppText>
            <Pressable testID="go-signup-link" onPress={() => router.push("/(auth)/signup")}>
              <AppText weight="bold" color={colors.brandPrimary}>Sign Up</AppText>
            </Pressable>
          </View>

          <LegalLinks style={{ marginTop: spacing.xxl, paddingBottom: insets.bottom + spacing.md }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
