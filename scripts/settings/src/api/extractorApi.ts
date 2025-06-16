import { ExtractorSchema, ExtractionPayload, ExtractionApiResponse } from '../types/extractors';

const API_BASE_URL = '/api/ui'; // Assuming backend is served from the same domain

/**
 * Fetches the available extractor schemas from the backend.
 */
export const fetchExtractorSchemas = async (): Promise<ExtractorSchema[]> => {
  const response = await fetch(`${API_BASE_URL}/extractors`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Failed to fetch extractor schemas. Network error or invalid JSON response.' }));
    throw new Error(errorData.message || `HTTP error ${response.status}`);
  }
  return response.json();
};

/**
 * Starts an extraction process by sending the payload to the backend.
 * @param payload - The data needed to start the extraction.
 */
export const startExtraction = async (payload: ExtractionPayload): Promise<ExtractionApiResponse> => {
  const response = await fetch(`${API_BASE_URL}/extract`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Extraction request failed. Network error or invalid JSON response.' }));
    // Enrich with status if possible and not already in message
    const errorMessage = errorData.message || `HTTP error ${response.status}`;
    // Throw an object that includes potential logs from backend error
    const errorToThrow: any = new Error(errorMessage);
    errorToThrow.response = errorData; // Attach full error response
    throw errorToThrow;
  }
  return response.json();
};
