import React from 'react';
import { Paper, Text, Title, List, ThemeIcon, ScrollArea, Code, Stack, Accordion } from '@mantine/core';
import { IconFileInfo, IconPhoto, IconVideo, IconMusic, IconFileText, IconQuestionMark, IconListDetails } from '@tabler/icons-react';
import { ExtractedData, MediaItem } from '../../types/extractors'; // Assuming ExtractedData can be an array for multiple results

interface ResultsDisplayProps {
  resultData: ExtractedData | ExtractedData[] | null; // Can be single or array
}

const getIconForType = (type: string | undefined) => {
  if (!type) return <IconQuestionMark size={16} />;
  if (type.startsWith('image')) return <IconPhoto size={16} />;
  if (type.startsWith('video')) return <IconVideo size={16} />;
  if (type.startsWith('audio')) return <IconMusic size={16} />;
  if (type.startsWith('text') || type === 'subtitle') return <IconFileText size={16} />;
  return <IconFileInfo size={16} />;
};


const SingleResultDisplay: React.FC<{result: ExtractedData, index?: number, totalItems?: number}> = ({ result, index, totalItems }) => {
  const titleText = result.metadata?.title || result.metadata?.text || "Untitled Extraction";
  const accordionLabel = totalItems && totalItems > 1 && index !== undefined
    ? `Item ${index + 1} of ${totalItems}: ${titleText}`
    : titleText;

  return (
    <Paper shadow="xs" p="md" mt="lg" withBorder>
      <Title order={4} mb="sm">{accordionLabel}</Title>

      <Text size="sm" color="dimmed" mb="xs">
        Extractor Info: {result.extractor_info || 'N/A'}
      </Text>

      <Accordion defaultValue="metadata" chevronPosition="left">
        <Accordion.Item value="metadata">
          <Accordion.Control icon={<IconListDetails size={20} />}>Metadata</Accordion.Control>
          <Accordion.Panel>
            <ScrollArea style={{ height: 200 }} type="auto">
              <Code block style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {JSON.stringify(result.metadata, null, 2) || 'No metadata available.'}
              </Code>
            </ScrollArea>
          </Accordion.Panel>
        </Accordion.Item>

        {result.media && result.media.length > 0 && (
           <Accordion.Item value="media">
           <Accordion.Control icon={getIconForType(result.media[0]?.type)}>Media ({result.media.length})</Accordion.Control>
           <Accordion.Panel>
            <List
                spacing="xs"
                size="sm"
                center={false} // Keep items aligned to the left
              >
                {result.media.map((item: MediaItem, idx: number) => (
                  <List.Item
                    key={idx}
                    icon={
                      <ThemeIcon color="blue" size={24} radius="xl">
                        {getIconForType(item.type)}
                      </ThemeIcon>
                    }
                  >
                    <Stack spacing={0}>
                      <Text weight={500}>{item.filepath || 'Filepath not available'}</Text>
                      <Text size="xs" color="dimmed">
                        Type: {item.type || 'N/A'}
                        {item.original_url && <>, Original URL: <Text component="a" href={item.original_url} target="_blank" rel="noopener noreferrer" variant="link">link</Text></>}
                      </Text>
                    </Stack>
                  </List.Item>
                ))}
              </List>
            </Accordion.Panel>
          </Accordion.Item>
        )}
      </Accordion>
    </Paper>
  );
}


const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ resultData }) => {
  if (!resultData) {
    return <Text mt="lg">No results yet, or extraction failed to produce data.</Text>;
  }

  const resultsArray = Array.isArray(resultData) ? resultData : [resultData];

  if (resultsArray.length === 0) {
      return <Text mt="lg">Extraction produced no items.</Text>;
  }

  if (resultsArray.length === 1) {
    return <SingleResultDisplay result={resultsArray[0]} />;
  }

  // Multiple results (e.g. playlist from GenericExtractor)
  return (
    <Stack mt="lg">
      <Title order={3}>Extraction Results ({resultsArray.length} items)</Title>
      {resultsArray.map((result, idx) => (
        <SingleResultDisplay key={idx} result={result} index={idx} totalItems={resultsArray.length} />
      ))}
    </Stack>
  );
};

export default ResultsDisplay;
