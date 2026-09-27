/* Chatly AI Messenger brand logo — vector twin of the app icon.
 *
 * Mark: orange gradient squircle carrying a white chat bubble with a
 * bottom-left tail, a 4-point AI spark inside and a smaller companion
 * spark — AI + messaging in one recognizable glyph.
 *
 * <Logo />       full mark (gradient squircle) — headers, auth screens
 * <LogoGlyph />  bubble + spark only — for use on brand/colored surfaces
 */
import React from "react";
import Svg, { Defs, LinearGradient, Stop, Rect, Path } from "react-native-svg";

const BUBBLE = "M254 420 Q254 324 350 324 L614 324 Q710 324 710 420 L710 528 Q710 624 614 624 L462 624 L354 720 L370 616 Q254 612 254 516 Z";

const sparkPath = (cx: number, cy: number, R: number, r: number) => {
  const p = (x: number, y: number) => `${x.toFixed(1)} ${y.toFixed(1)}`;
  return [
    `M${p(cx, cy - R)}`,
    `Q${p(cx + r * 0.15, cy - r * 0.15)} ${p(cx + r, cy - r)}`,
    `Q${p(cx + r * 0.15, cy - r * 0.15)} ${p(cx + R, cy)}`,
    `Q${p(cx + r * 0.15, cy + r * 0.15)} ${p(cx + r, cy + r)}`,
    `Q${p(cx + r * 0.15, cy + r * 0.15)} ${p(cx, cy + R)}`,
    `Q${p(cx - r * 0.15, cy + r * 0.15)} ${p(cx - r, cy + r)}`,
    `Q${p(cx - r * 0.15, cy + r * 0.15)} ${p(cx - R, cy)}`,
    `Q${p(cx - r * 0.15, cy - r * 0.15)} ${p(cx - r, cy - r)}`,
    `Q${p(cx - r * 0.15, cy - r * 0.15)} ${p(cx, cy - R)}`,
    "Z",
  ].join(" ");
};

export function LogoGlyph({
  size = 32,
  bubble = "#FFFFFF",
  spark = "#FF5E00",
}: { size?: number; bubble?: string; spark?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 1024 1024" fill="none">
      <Path d={BUBBLE} fill={bubble} />
      <Path d={sparkPath(486, 478, 108, 34)} fill={spark} />
      <Path d={sparkPath(630, 402, 52, 17)} fill={spark} />
    </Svg>
  );
}

export function Logo({ size = 72 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 1024 1024" fill="none">
      <Defs>
        <LinearGradient id="chatlyBrand" x1="0" y1="0" x2="1024" y2="1024">
          <Stop offset="0" stopColor="#FF8C42" />
          <Stop offset="1" stopColor="#FF5E00" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="1024" height="1024" rx="228" fill="url(#chatlyBrand)" />
      <Path d={BUBBLE} fill="#FFFFFF" />
      <Path d={sparkPath(486, 478, 108, 34)} fill="#FF5E00" />
      <Path d={sparkPath(630, 402, 52, 17)} fill="#FF5E00" />
    </Svg>
  );
}
