import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../../src/theme';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#000',
          borderTopColor: Colors.borderGlow,
          borderTopWidth: 1,
          height: 64,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarLabelStyle: { fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'STATUS',
          tabBarIcon: ({ color }) => <Ionicons name="grid-outline" size={22} color={color} />,
        }}
      />
      <Tabs.Screen
        name="quest"
        options={{
          title: 'QUEST',
          tabBarIcon: ({ color }) => <Ionicons name="flash-outline" size={22} color={color} />,
        }}
      />
      <Tabs.Screen
        name="progress"
        options={{
          title: 'PROGRESS',
          tabBarIcon: ({ color }) => <Ionicons name="trending-up-outline" size={22} color={color} />,
        }}
      />
      <Tabs.Screen
        name="rank"
        options={{
          title: 'RANK',
          tabBarIcon: ({ color }) => <Ionicons name="ribbon-outline" size={22} color={color} />,
        }}
      />
    </Tabs>
  );
}
