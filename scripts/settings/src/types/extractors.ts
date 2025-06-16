// Types for the Extractor UI

export interface ParamSchema {
  name: string;
  label: string;
  type: 'text' | 'boolean' | 'textarea' | 'password' | 'number'; // 'checkbox' maps to boolean, 'number' for numeric input
  default: any;
  help_text?: string;
}

export interface ExtractorSchema {
  id: string;
  name: string;
  description: string;
  params: ParamSchema[];
}

// Represents the structure of a single media item in the results
export interface MediaItem {
  filepath: string;
  type: string;
  original_url?: string;
  // Add other media-specific fields if returned by backend and needed by UI
  [key: string]: any;
}

// Represents the structure of the "metadata" part of the result
export interface ResultMetadata {
  title?: string;
  text?: string; // For Twitter, title might be the text
  // Add other common or specific metadata fields
  [key: string]: any;
}

// Represents the structure of the successful data from /api/ui/extract
// This can be a single object or an array of such objects (e.g., for playlists)
export interface ExtractedData {
  metadata: ResultMetadata;
  media: MediaItem[];
  extractor_info: string;
  // Include other fields if the backend adds them to each item in the list
}

// The payload for the POST /api/ui/extract endpoint
export interface ExtractionPayload {
  extractor_id: string;
  url: string;
  output_path: string;
  config_values: Record<string, any>;
}

// The structure of the response from POST /api/ui/extract
// (assuming data can be single or list based on GenericExtractor's potential output)
export interface ExtractionApiResponse {
  status: 'success' | 'error';
  data?: ExtractedData | ExtractedData[]; // Backend might return single or list
  message?: string;
  logs?: string[];
}
