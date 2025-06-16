import React, { useState, useEffect, useCallback } from 'react';
import { Container, Title, Paper, Stack, Group, Alert, Loader, Divider } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';

import { ExtractorSchema, ExtractedData, ParamSchema, ExtractionPayload } from '../types/extractors';
import { fetchExtractorSchemas, startExtraction } from '../api/extractorApi';

import ExtractorSelector from '../components/ExtractorUI/ExtractorSelector';
import DynamicConfigForm from '../components/ExtractorUI/DynamicConfigForm';
import ExtractionInputForm from '../components/ExtractorUI/ExtractionInputForm';
import ResultsDisplay from '../components/ExtractorUI/ResultsDisplay';
import LogDisplay from '../components/ExtractorUI/LogDisplay';

const ExtractorUIPage: React.FC = () => {
  const [extractorSchemas, setExtractorSchemas] = useState<ExtractorSchema[]>([]);
  const [selectedExtractorId, setSelectedExtractorId] = useState<string | null>(null);
  const [configValues, setConfigValues] = useState<Record<string, any>>({});
  const [url, setUrl] = useState<string>('');
  // TODO: Consider making default output_path configurable or user-specific if security is a concern.
  // For now, it's an empty string requiring user input.
  const [outputPath, setOutputPath] = useState<string>('');
  const [extractionResult, setExtractionResult] = useState<ExtractedData | ExtractedData[] | null>(null);
  const [extractionLogs, setExtractionLogs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSchemasLoading, setIsSchemasLoading] = useState<boolean>(true);


  const currentSchema = extractorSchemas.find(s => s.id === selectedExtractorId) || null;

  // Fetch schemas on mount
  useEffect(() => {
    setIsSchemasLoading(true);
    fetchExtractorSchemas()
      .then(schemas => {
        setExtractorSchemas(schemas);
        if (schemas.length > 0) {
          // Select the first extractor by default
          const firstSchema = schemas[0];
          setSelectedExtractorId(firstSchema.id);
          // Initialize configValues with defaults from the first schema
          const initialConfigs: Record<string, any> = {};
          firstSchema.params.forEach(param => {
            initialConfigs[param.name] = param.default;
          });
          setConfigValues(initialConfigs);
        }
        setIsSchemasLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch extractor schemas:", err);
        setError(`Failed to load extractor configurations: ${err.message}`);
        setIsSchemasLoading(false);
      });
  }, []);

  const handleExtractorSelect = useCallback((id: string) => {
    setSelectedExtractorId(id);
    const schema = extractorSchemas.find(s => s.id === id);
    if (schema) {
      const initialConfigs: Record<string, any> = {};
      schema.params.forEach(param => {
        initialConfigs[param.name] = param.default;
      });
      setConfigValues(initialConfigs);
    } else {
      setConfigValues({});
    }
    setExtractionResult(null); // Clear previous results
    setExtractionLogs([]);
    setError(null);
  }, [extractorSchemas]);

  const handleConfigChange = useCallback((fieldName: string, value: any) => {
    setConfigValues(prev => ({ ...prev, [fieldName]: value }));
  }, []);

  const handleSubmitExtraction = useCallback(async () => {
    if (!selectedExtractorId || !url || !outputPath) {
      setError("Please select an extractor, enter a URL, and provide an output path.");
      return;
    }

    setIsLoading(true);
    setExtractionResult(null);
    setExtractionLogs(["Starting extraction..."]);
    setError(null);

    const payload: ExtractionPayload = {
      extractor_id: selectedExtractorId,
      url,
      output_path: outputPath,
      config_values: configValues,
    };

    try {
      const response = await startExtraction(payload);
      if (response.status === 'success') {
        setExtractionResult(response.data || null); // data can be ExtractedData or ExtractedData[]
        setExtractionLogs(prev => [...prev, "Extraction successful!", ...(response.logs || [])]);
      } else {
        setError(response.message || "Extraction failed with no specific message.");
        setExtractionLogs(prev => [...prev, `Error: ${response.message}`, ...(response.logs || [])]);
      }
    } catch (err: any) {
      console.error("Extraction API error:", err);
      const errorMessage = err.message || "An unknown error occurred during extraction.";
      setError(errorMessage);
      // If backend error response contains logs, try to display them
      const responseLogs = err.response?.logs || (typeof err.response?.message === 'string' ? [err.response.message] : []);
      setExtractionLogs(prev => [...prev, `Failed: ${errorMessage}`, ...responseLogs]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedExtractorId, url, outputPath, configValues]);

  if (isSchemasLoading) {
    return <Container><Group position="center" mt="xl"><Loader /></Group></Container>;
  }

  return (
    <Container size="md" my="xl">
      <Stack spacing="xl">
        <Title order={2} align="center">Extractor UI</Title>

        {extractorSchemas.length > 0 && selectedExtractorId && (
          <Paper shadow="sm" p="lg" withBorder>
            <ExtractorSelector
              schemas={extractorSchemas}
              selectedId={selectedExtractorId}
              onSelect={handleExtractorSelect}
            />
          </Paper>
        )}

        {currentSchema && (
          <Paper shadow="sm" p="lg" withBorder>
            <Title order={4} mb="md">{currentSchema.name} Configuration</Title>
            <Text size="sm" color="dimmed" mb="md">{currentSchema.description}</Text>
            <DynamicConfigForm
              schema={currentSchema}
              configValues={configValues}
              onConfigChange={handleConfigChange}
            />
          </Paper>
        )}

        <Paper shadow="sm" p="lg" withBorder>
           <Title order={4} mb="md">Extraction Target</Title>
          <ExtractionInputForm
            url={url}
            onUrlChange={setUrl}
            outputPath={outputPath}
            onOutputPathChange={setOutputPath}
            onSubmit={handleSubmitExtraction}
            isLoading={isLoading}
          />
        </Paper>

        {error && (
          <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red" withCloseButton onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {isLoading && <Group position="center" mt="md"><Loader /></Group>}

        {(extractionResult || extractionLogs.length > (isLoading ? 1:0) ) && <Divider my="lg" label="Results & Logs" labelPosition="center" />}

        {extractionResult && (
          <ResultsDisplay resultData={extractionResult} />
        )}

        {extractionLogs.length > (isLoading ? 1:0) && !extractionResult && !error && !isLoading &&(
          <Text mt="md">Extraction finished, but no structured data was returned. Check logs for details.</Text>
        )}

        {extractionLogs.length > 0 && (
           <LogDisplay logs={extractionLogs} />
        )}

      </Stack>
    </Container>
  );
};

export default ExtractorUIPage;
