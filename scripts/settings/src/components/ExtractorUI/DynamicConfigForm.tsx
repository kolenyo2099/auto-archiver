import React from 'react';
import { TextInput, Checkbox, Textarea, PasswordInput, NumberInput, Stack, Tooltip, Text } from '@mantine/core';
import { IconHelpCircle } from '@tabler/icons-react';
import { ExtractorSchema, ParamSchema } from '../../types/extractors';

interface DynamicConfigFormProps {
  schema: ExtractorSchema | null;
  configValues: Record<string, any>;
  onConfigChange: (fieldName: string, value: any) => void;
}

const DynamicConfigForm: React.FC<DynamicConfigFormProps> = ({ schema, configValues, onConfigChange }) => {
  if (!schema) {
    return <Text>Select an extractor to see its configuration options.</Text>;
  }

  const renderParamInput = (param: ParamSchema) => {
    const commonProps = {
      key: param.name,
      label: param.label,
      description: param.help_text ? (
        <Text size="xs" color="dimmed">
          {param.help_text}
        </Text>
      ) : null,
      // Removed direct rightSection for Tooltip to avoid layout issues with some inputs
      // Tooltip can be added around the label or help icon if complex help is needed.
    };

    const helpIcon = param.help_text ? (
      <Tooltip label={param.help_text} withArrow multiline width={220}>
        <IconHelpCircle size={16} style={{ marginLeft: 5, cursor: 'help', verticalAlign: 'middle' }} />
      </Tooltip>
    ) : null;

    const labelWithHelp = (
      <>
        {param.label}
        {helpIcon}
      </>
    );


    switch (param.type) {
      case 'text':
        return (
          <TextInput
            {...commonProps}
            label={labelWithHelp}
            description={null} // Help text is part of labelWithHelp or can be separate Text
            value={configValues[param.name] || ''}
            onChange={(event) => onConfigChange(param.name, event.currentTarget.value)}
          />
        );
      case 'boolean': // Render as Checkbox
        return (
          <Checkbox
            {...commonProps}
            label={labelWithHelp}
            description={null}
            checked={configValues[param.name] || false}
            onChange={(event) => onConfigChange(param.name, event.currentTarget.checked)}
            mt="xs" // Add some margin for checkboxes for better alignment
          />
        );
      case 'textarea':
        return (
          <Textarea
            {...commonProps}
            label={labelWithHelp}
            description={null}
            value={configValues[param.name] || ''}
            onChange={(event) => onConfigChange(param.name, event.currentTarget.value)}
            autosize
            minRows={2}
          />
        );
      case 'password':
        return (
          <PasswordInput
            {...commonProps}
            label={labelWithHelp}
            description={null}
            value={configValues[param.name] || ''}
            onChange={(event) => onConfigChange(param.name, event.currentTarget.value)}
          />
        );
      case 'number': // Assuming 'number' type was added to ParamSchema
         return (
           <NumberInput
            {...commonProps}
            label={labelWithHelp}
            description={null}
            value={configValues[param.name] === undefined ? (param.default !== undefined ? Number(param.default) : undefined) : Number(configValues[param.name])}
            onChange={(value) => onConfigChange(param.name, value === undefined ? null : Number(value))} // value can be string or number from NumberInput
           />
         );
      default:
        return (
          <TextInput
            {...commonProps}
            label={`${labelWithHelp} (Unsupported type: ${param.type})`}
            description={null}
            value={configValues[param.name] || ''}
            onChange={(event) => onConfigChange(param.name, event.currentTarget.value)}
            error={`Unsupported type: ${param.type}`}
          />
        );
    }
  };

  return (
    <Stack spacing="md" mt="md">
      {schema.params.length > 0 ? (
        schema.params.map(renderParamInput)
      ) : (
        <Text>This extractor has no configurable parameters.</Text>
      )}
    </Stack>
  );
};

export default DynamicConfigForm;
