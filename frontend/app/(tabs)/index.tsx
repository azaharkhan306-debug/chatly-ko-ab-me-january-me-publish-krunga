import { useEffect, useState, useCallback, useMemo, memo } from "react";
import { View, FlatList, Pressable, RefreshControl, TextInput, StyleSheet, Modal } from "react-native";
import { useRouter } from "expo-router";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme, spacing, radius, fontSize } from "@/src/theme";
import { SwipeNav } from "@/src/SwipeNav";
import { AppText, Avatar, Icon, EmptyState, Skeleton } from "@/src/ui";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useWs } from "@/src/ws";
import { storage } from "@/src/utils/storage";
import dayjs from "dayjs";

type Chat = {
  chat_id: string;
  other: { user_id: string; name: string; avatar?: string; online?: boolean; is_bot?: boolean };
  last_message?: string;
  last_ts?: string;
  unread: number;
  pinned: boolean;
};

export default function Chats() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { subscribe } = useWs();
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Chat | null>(null);

  const doDelete = async () => {
    const t = deleteTarget; setDeleteTarget(null);
    if (!t) return;
    setChats((p) => p.filter((c) => c.chat_id !== t.chat_id));
    try { await api.del(`/chats/${t.chat_id}`); } catch { load(); }
  };

  const load = useCallback(async () => {
    setError(false);
    // Hydrate the cached list instantly so the screen never shows a
    // "check connection" dead-end when the request is merely slow.
    if (!chats.length) {
      const cached = await storage.getItem<Chat[] | null>("chatly_chats_cache", null);
      if (cached?.length) { setChats(cached); setLoading(false); }
    }
    // Retry network/timeout failures automatically (2 extra attempts).
    let lastErr: any = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const res = await api.get<{ chats: Chat[] }>("/chats");
        setChats(res.chats);
        storage.setItem("chatly_chats_cache", res.chats as any);
        setError(false);
        setLoading(false); setRefreshing(false);
        return;
      } catch (e: any) {
        lastErr = e;
        const transient = !e?.status || e.category === "network" || e.category === "timeout";
        if (!transient || attempt === 2) break;
        await new Promise((r) => setTimeout(r, 900 * (attempt + 1)));
      }
    }
    if (lastErr) setError(true);
    setLoading(false); setRefreshing(false);
  }, [chats.length]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  // Auto-reload when the network returns (Wi-Fi <-> data switches, flight mode).
  useEffect(() => {
    let NetInfo: any = null;
    try { NetInfo = require("@react-native-community/netinfo"); } catch {}
    if (!NetInfo?.addEventListener) return;
    const unsub = NetInfo.addEventListener((state: any) => {
      if (state?.isInternetReachable) load();
    });
    return () => { try { unsub(); } catch {} };
  }, [load]);

  // Realtime updates: patch the affected row IN PLACE instead of refetching the
  // whole list on every incoming message (the old behaviour made one full
  // /chats request per received message — heavy and laggy in active chats).
  // A full refresh only happens for unknown chats (new conversation) and on
  // focus / pull-to-refresh.
  const { user } = useAuth();
  const myId = user?.user_id;
  useEffect(() => subscribe((ev) => {
    if (ev.type !== "message") return;
    const m = ev.message;
    if (!m?.chat_id) return;
    setChats((prev) => {
      const idx = prev.findIndex((c) => c.chat_id === m.chat_id);
      if (idx < 0) { load(); return prev; } // brand-new chat -> full refresh
      const row = prev[idx];
      const bumpUnread = m.sender_id && m.sender_id !== myId ? 1 : 0;
      const updated: Chat = {
        ...row,
        last_message: m.deleted ? "This message was deleted" : (m.text || row.last_message),
        last_ts: m.created_at || row.last_ts,
        unread: (row.unread || 0) + bumpUnread,
      };
      return [updated, ...prev.filter((_, i) => i !== idx)]; // most-recent first
    });
  }), [subscribe, load, myId]);

  const sorted = useMemo(() => {
    const f = chats.filter((c) => c.other?.name?.toLowerCase().includes(query.toLowerCase()));
    return [...f].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
  }, [chats, query]);


  const onRowPress = useCallback((row: Chat) => {
    router.push({ pathname: "/chat/[id]", params: { id: row.chat_id, name: row.other?.name } });
  }, [router]);

  return (
    <SwipeNav tab="index">
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <View style={{ paddingTop: insets.top + spacing.sm, paddingHorizontal: spacing.lg, paddingBottom: spacing.sm, backgroundColor: colors.surface }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.md }}>
          <AppText size="xxxl" weight="heavy">Chats</AppText>
          <Pressable testID="new-chat-button" onPress={() => router.push("/new-chat")} style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
            <Icon name="create-outline" size={22} color={colors.brandPrimary} />
          </Pressable>
        </View>
        <View style={[styles.search, { backgroundColor: colors.surfaceTertiary }]}>
          <Icon name="search" size={18} color={colors.onSurfaceMuted} />
          <TextInput
            testID="chat-search-input"
            value={query}
            onChangeText={setQuery}
            placeholder="Search chats"
            placeholderTextColor={colors.onSurfaceMuted}
            style={{ flex: 1, marginLeft: 8, color: colors.onSurface, fontSize: fontSize.lg, paddingVertical: 0 }}
          />
        </View>
      </View>

      {loading ? (
        <View style={{ padding: spacing.lg, gap: spacing.md }}>
          {[...Array(6)].map((_, i) => <Skeleton key={i} height={64} />)}
        </View>
      ) : error ? (
        <EmptyState icon="cloud-offline-outline" title="Unable to load chats" subtitle="Check your connection and try again" action={<Pressable testID="retry-chats" onPress={load}><AppText weight="bold" color={colors.brandPrimary}>Retry</AppText></Pressable>} />
      ) : sorted.length === 0 ? (
        <EmptyState icon="chatbubbles-outline" title="No conversations yet" subtitle="Start a chat and let Chatly turn messages into tasks, summaries and more." />
      ) : (
        <FlatList
          data={sorted}
          keyExtractor={(c) => c.chat_id}
          renderItem={({ item }) => <ChatRow item={item} onPress={onRowPress} onLongPress={setDeleteTarget} colors={colors} />}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
          contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingBottom: spacing.xl }}
          ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: colors.divider, marginLeft: 66 }} />}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={colors.brandPrimary} />}
        />
      )}

      {/* Long-press chat actions */}
      <Modal visible={!!deleteTarget} transparent animationType="fade" onRequestClose={() => setDeleteTarget(null)}>
        <Pressable style={{ flex: 1, backgroundColor: colors.overlay, alignItems: "center", justifyContent: "center", padding: spacing.xl }} onPress={() => setDeleteTarget(null)}>
          <View style={{ backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.xl, width: "100%" }}>
            <AppText weight="bold" size="lg" center numberOfLines={1}>{deleteTarget?.other?.name}</AppText>
            <AppText muted center style={{ marginTop: spacing.sm, marginBottom: spacing.lg }}>Delete this chat? It reappears if you receive a new message.</AppText>
            <Pressable testID="confirm-delete-chat-row" onPress={doDelete} style={{ height: 48, borderRadius: radius.md, backgroundColor: colors.error, alignItems: "center", justifyContent: "center" }}>
              <AppText weight="bold" color="#fff">Delete Chat</AppText>
            </Pressable>
            <Pressable onPress={() => setDeleteTarget(null)} style={{ marginTop: spacing.md, alignItems: "center" }}><AppText weight="semibold">Cancel</AppText></Pressable>
          </View>
        </Pressable>
      </Modal>
    </View>
    </SwipeNav>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.md, borderRadius: radius.md },
  search: { flexDirection: "row", alignItems: "center", height: 44, borderRadius: radius.pill, paddingHorizontal: spacing.md },
});

// Memoized chat row — re-renders only when its own chat data changes.
const ChatRow = memo(function ChatRow({ item, onPress, onLongPress, colors: c }: any) {
  return (
    <Pressable
      testID={`chat-row-${item.other?.user_id}`}
      onPress={() => onPress(item)}
      onLongPress={() => onLongPress(item)}
      delayLongPress={350}
      style={({ pressed }) => [styles.row, { backgroundColor: pressed ? c.surfaceTertiary : "transparent" }]}
    >
      <Avatar name={item.other?.name} uri={item.other?.avatar} size={54} online={item.other?.online} />
      <View style={{ flex: 1, marginLeft: spacing.md }}>
        <View style={{ flexDirection: "row", alignItems: "center" }}>
          <AppText weight="semibold" size="lg" style={{ flex: 1 }} numberOfLines={1}>{item.other?.name}</AppText>
          <AppText size="sm" muted>{item.last_ts ? dayjs(item.last_ts).format("HH:mm") : ""}</AppText>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", marginTop: 3 }}>
          <AppText muted size="base" style={{ flex: 1 }} numberOfLines={1}>{item.last_message || "Tap to start chatting"}</AppText>
          {item.pinned && <Icon name="pin" size={14} color={c.onSurfaceMuted} />}
          {item.unread > 0 && (
            <View style={{ backgroundColor: c.brandPrimary, borderRadius: 11, minWidth: 22, height: 22, alignItems: "center", justifyContent: "center", paddingHorizontal: 6, marginLeft: 6 }}>
              <AppText size="xs" weight="bold" color="#fff">{item.unread}</AppText>
            </View>
          )}
        </View>
      </View>
    </Pressable>
  );
});
