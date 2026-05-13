import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { askCoach } from '../src/api';

export default function AICoach() {
  const router = useRouter();
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ q?: string; a: string }[]>([]);

  const ask = async (q?: string) => {
    const pid = await AsyncStorage.getItem('profile_id');
    if (!pid) return;
    setLoading(true);
    try {
      const r = await askCoach(pid, q);
      setMessages([{ q, a: r.response }, ...messages]);
      setQuestion('');
    } catch (e: any) {
      setMessages([{ q, a: '[SYSTEM OFFLINE] Try again.' }, ...messages]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} testID="btn-back">
            <Ionicons name="chevron-back" size={24} color={Colors.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1, marginLeft: 8 }}>
            <Text style={styles.system}>[NEURAL LINK ACTIVE]</Text>
            <Text style={styles.title}>SYSTEM COACH</Text>
          </View>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <SystemFrame style={styles.intro}>
            <Text style={styles.introTxt}>
              {">"} I am The System. I observe your quests, your fatigue, your power.{'\n'}
              {">"} Ask me anything. Or request a tactical analysis below.
            </Text>
          </SystemFrame>

          <TouchableOpacity
            testID="btn-quick-analysis"
            style={styles.quickBtn}
            onPress={() => ask()}
            disabled={loading}
          >
            <Ionicons name="flash" size={16} color={Colors.primary} />
            <Text style={styles.quickTxt}>ANALYZE LAST QUEST</Text>
          </TouchableOpacity>

          {loading && (
            <View style={styles.loading}>
              <ActivityIndicator color={Colors.primary} />
              <Text style={styles.loadingTxt}>[SYSTEM PROCESSING...]</Text>
            </View>
          )}

          {messages.map((m, i) => (
            <View key={i} style={{ marginTop: 16 }}>
              {m.q && (
                <View style={styles.userMsg}>
                  <Text style={styles.userTxt}>{m.q}</Text>
                </View>
              )}
              <SystemFrame style={styles.coachMsg}>
                <Text style={styles.coachTag}>[SYSTEM]</Text>
                <Text style={styles.coachTxt}>{m.a}</Text>
              </SystemFrame>
            </View>
          ))}
        </ScrollView>

        <View style={styles.inputBar}>
          <TextInput
            testID="input-question"
            value={question}
            onChangeText={setQuestion}
            placeholder="Ask the System..."
            placeholderTextColor={Colors.textDim}
            style={styles.input}
          />
          <TouchableOpacity
            testID="btn-send"
            onPress={() => question.trim() && ask(question.trim())}
            style={styles.sendBtn}
            disabled={loading}
          >
            <Ionicons name="send" size={18} color={Colors.primary} />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 20, letterSpacing: 2, marginTop: 2 },
  scroll: { padding: 16, paddingBottom: 20 },
  intro: { marginBottom: 16 },
  introTxt: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 12, lineHeight: 18 },
  quickBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.06)' },
  quickTxt: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 13, letterSpacing: 3 },
  loading: { alignItems: 'center', marginTop: 16, gap: 8 },
  loadingTxt: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 2 },
  userMsg: { alignSelf: 'flex-end', backgroundColor: 'rgba(0,255,255,0.06)', borderWidth: 1, borderColor: Colors.borderGlow, padding: 10, maxWidth: '85%' },
  userTxt: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 12 },
  coachMsg: { marginTop: 10 },
  coachTag: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 3, marginBottom: 6 },
  coachTxt: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 13, lineHeight: 19 },
  inputBar: { flexDirection: 'row', padding: 12, borderTopWidth: 1, borderTopColor: Colors.border, backgroundColor: '#000', alignItems: 'center', gap: 8 },
  input: { flex: 1, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, color: Colors.textMain, fontFamily: Fonts.mono, padding: 12, fontSize: 13 },
  sendBtn: { width: 48, height: 44, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
});
