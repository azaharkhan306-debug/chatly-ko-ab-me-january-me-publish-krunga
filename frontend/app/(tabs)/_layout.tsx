import { Tabs } from "expo-router";
import { Platform, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/src/theme";

// Swipe navigation between the five tabs (Chats -> Chatly -> Status -> Calls ->
// Profile, linear) lives in src/SwipeNav.tsx and is rendered INSIDE each tab
// screen with a static tab identity — reliable on both web and native.
export default function TabsLayout() {
  const { colors } = useTheme();

  return (
    <View style={{ flex: 1 }}>
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: colors.brandPrimary,
          tabBarInactiveTintColor: colors.onSurfaceMuted,
          tabBarStyle: {
            backgroundColor: colors.card,
            borderTopColor: colors.border,
            ...(Platform.OS === "web" ? { height: 64 } : {}),
          },
          tabBarItemStyle: { alignSelf: "center" },
          tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
        }}
      >
        <Tabs.Screen name="index" options={{ title: "Chats", tabBarIcon: ({ color, size }) => <Ionicons name="chatbubbles" size={size} color={color} /> }} />
        <Tabs.Screen name="chatly" options={{ title: "Chatly", tabBarIcon: ({ color, size }) => <Ionicons name="sparkles" size={size} color={color} /> }} />
        <Tabs.Screen name="status" options={{ title: "Status", tabBarIcon: ({ color, size }) => <Ionicons name="radio" size={size} color={color} /> }} />
        <Tabs.Screen name="calls" options={{ title: "Calls", tabBarIcon: ({ color, size }) => <Ionicons name="call" size={size} color={color} /> }} />
        <Tabs.Screen name="profile" options={{ title: "Profile", tabBarIcon: ({ color, size }) => <Ionicons name="person" size={size} color={color} /> }} />
      </Tabs>
    </View>
  );
}
