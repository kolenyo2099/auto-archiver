import React from 'react';
import { TextInput, Button, Group, Stack } from '@mantine/core';

interface ExtractionInputFormProps {
  url: string;
  onUrlChange: (val: string) => void;
  outputPath: string;
  onOutputPathChange: (val: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

const ExtractionInputForm: React.FC<ExtractionInputFormProps> = ({
  url,
  onUrlChange,
  outputPath,
  onOutputPathChange,
  onSubmit,
  isLoading,
}) => {
  return (
    <Stack spacing="md" mt="lg">
      <TextInput
        label="Content URL"
        placeholder="Enter the URL of the content to extract"
        value={url}
        onChange={(event) => onUrlChange(event.currentTarget.value)}
        required
      />
      <TextInput
        label="Output Path"
        placeholder="Enter the absolute local path to save media"
        value={outputPath}
        onChange={(event) => onOutputPathChange(event.currentTarget.value)}
        required
        description="Must be an absolute path on the server where auto-archiver is running."
      />
      <Group position="right" mt="md">
        <Button onClick={onSubmit} loading={isLoading} disabled={!url || !outputPath}>
          Start Extraction
        </Button>
      </Group>
    </Stack>
  );
};

export default ExtractionInputForm;
