import React from 'react';
import { Select } from '@mantine/core';
import { ExtractorSchema } from '../../types/extractors';

interface ExtractorSelectorProps {
  schemas: ExtractorSchema[];
  selectedId: string | null; // Allow null for initial state
  onSelect: (id: string) => void;
}

const ExtractorSelector: React.FC<ExtractorSelectorProps> = ({ schemas, selectedId, onSelect }) => {
  const data = schemas.map(schema => ({
    value: schema.id,
    label: schema.name,
  }));

  return (
    <Select
      label="Choose Extractor"
      placeholder="Select an extractor"
      data={data}
      value={selectedId}
      onChange={(value) => {
        if (value) { // Ensure value is not null before calling onSelect
          onSelect(value);
        }
      }}
      searchable
      clearable={false} // Or true if you want to allow clearing selection
    />
  );
};

export default ExtractorSelector;
