/* Horizontal swipe navigation between the 5 main tabs.
 *
 * Rendered INSIDE each tab screen with a STATIC `tab` prop (each screen file
 * knows its own identity), so there is no state tracking to go stale:
 *   Chats -> Chatly -> Status -> Calls -> Profile   (left swipe = next)
 *   reverse for right swipe, no wrap-around at the ends.
 *
 * The Pan gesture is horizontal-only (activeOffsetX) and explicitly fails for
 * vertical drags (failOffsetY), so vertical scrolling in lists, chats and
 * status always wins. Taps, inputs, long-presses and media gestures are
 * unaffected.
 */
import React, { ReactNode, useCallback } from "react";
import { View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { runOnJS } from "react-native-reanimated";
import { useRouter } from "expo-router";

const ORDER = ["index", "chatly", "status", "calls", "profile"];
const PATHS: Record<string, string> = {
  index: "/",
  chatly: "/chatly",
  status: "/status",
  calls: "/calls",
  profile: "/profile",
};

export function SwipeNav({ tab, children }: { tab: string; children: ReactNode }) {
  const router = useRouter();

  const go = useCallback(
    (dir: number) => {
      const idx = ORDER.indexOf(tab);
      if (idx < 0) return;
      const next = ORDER[idx + dir];
      if (!next) return; // linear: no wrap-around at the ends
      router.navigate(PATHS[next] as any);
    },
    [router, tab],
  );

  const swipe = Gesture.Pan()
    .activeOffsetX([-30, 30])
    .failOffsetY([-14, 14])
    .onEnd((e) => {
      "worklet";
      if (e.translationX <= -55 && Math.abs(e.velocityX) > 120) runOnJS(go)(1);
      else if (e.translationX >= 55 && Math.abs(e.velocityX) > 120) runOnJS(go)(-1);
    });

  return (
    <GestureDetector gesture={swipe}>
      <View style={{ flex: 1 }}>{children}</View>
    </GestureDetector>
  );
}
