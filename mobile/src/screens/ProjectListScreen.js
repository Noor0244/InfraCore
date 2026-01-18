import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

export default function ProjectListScreen({ navigation }) {
  // Placeholder for project list
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Projects</Text>
      <TouchableOpacity style={styles.projectCard} onPress={() => navigation.navigate('Dashboard')}>
        <Text style={styles.projectName}>Sample Project 1</Text>
        <Text style={styles.projectMeta}>NH-66 Upgrade</Text>
      </TouchableOpacity>
      {/* Add more project cards here */}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#fff' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 24 },
  projectCard: { backgroundColor: '#f2f2f2', padding: 16, borderRadius: 8, marginBottom: 16 },
  projectName: { fontSize: 18, fontWeight: 'bold' },
  projectMeta: { fontSize: 14, color: '#666' },
});
