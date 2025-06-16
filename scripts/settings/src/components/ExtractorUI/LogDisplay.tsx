import React from 'react';
import { Paper, Text, ScrollArea, Title } from '@mantine/core';

interface LogDisplayProps {
  logs: string[];
}

const LogDisplay: React.FC<LogDisplayProps> = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return <Text mt="md">No logs to display.</Text>;
  }

  return (
    <Paper shadow="xs" p="md" mt="lg" withBorder>
      <Title order={5} mb="xs">Extraction Logs</Title>
      <ScrollArea style={{ height: 200 }} type="auto">
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.85em' }}>
          {logs.join('\n')}
        </pre>
      </ScrollArea>
    </Paper>
  );
};

export default LogDisplay;
