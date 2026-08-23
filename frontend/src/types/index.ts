export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type CaseStatus = 
  | 'OPEN' 
  | 'INVESTIGATING' 
  | 'REVIEW_REQUIRED' 
  | 'VERIFIED' 
  | 'NOT_VERIFIED';

export type PktUploadStatus = 
  | 'STORED' 
  | 'STORED_ENCRYPTED'
  | 'EXTRACTED' 
  | 'PARTIAL' 
  | 'FAILED';

export type FactSource = 
  | 'PKT_EXTRACTED' 
  | 'CISCO_EVIDENCE' 
  | 'USER_INPUT' 
  | 'PYTHON_RULE' 
  | 'AI_DIAGNOSIS' 
  | 'UNKNOWN' 
  | 'INSUFFICIENT_EVIDENCE';

export type ConnectionStatus = 'CONNECTED' | 'DISCONNECTED' | 'UNKNOWN';

export type AnalysisStatus = 'SUCCESS' | 'PARTIAL' | 'UNAVAILABLE' | 'FAILED';

export interface DeviceFact {
  name: string;
  device_type: string;
  model?: string | null;
  hostname?: string | null;
  source: FactSource;
}

export interface InterfaceFact {
  device: string;
  name: string;
  ip?: string | null;
  mask?: string | null;
  status: string;
  protocol: string;
  vlan_id?: number | null;
  mac_address?: string | null;
  source: FactSource;
}

export interface ConnectionFact {
  device_a: string;
  interface_a: string;
  device_b: string;
  interface_b: string;
  status: ConnectionStatus;
  link_type?: string | null;
  source: FactSource;
}

export interface VlanFact {
  vlan_id: number;
  name?: string | null;
  status: string;
  device?: string | null;
  source: FactSource;
}

export interface RouteFact {
  device: string;
  network: string;
  mask?: string | null;
  next_hop?: string | null;
  interface?: string | null;
  protocol?: string | null;
  metric?: number | null;
  source: FactSource;
}

export interface GatewayFact {
  device: string;
  gateway_ip?: string | null;
  source: FactSource;
}

export interface NormalizedNetworkFacts {
  devices: DeviceFact[];
  interfaces: InterfaceFact[];
  connections: ConnectionFact[];
  vlans: VlanFact[];
  routes: RouteFact[];
  gateways: GatewayFact[];
  networks: string[];
  source: FactSource;
}

export interface PktAnalysisResult {
  status: AnalysisStatus;
  source: FactSource;
  facts: NormalizedNetworkFacts;
  unsupported_fields: string[];
  warnings: string[];
  extraction_details: Record<string, any>;
  extracted_at: string;
}

export interface PktFile {
  id: number;
  case_id: number;
  pkt_filename: string;
  pkt_storage_path: string;
  pkt_file_size: number;
  pkt_uploaded_at: string;
  pkt_upload_status: PktUploadStatus;
  sha256_hash?: string;
}

export interface Case {
  id: number;
  case_number: string;
  title: string;
  category: string;
  severity: SeverityLevel;
  symptom: string;
  topology_notes?: string;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  pkt_file?: PktFile | null;
}

export interface CaseCreateInput {
  case_number?: string;
  title: string;
  category: string;
  severity: SeverityLevel;
  symptom: string;
  topology_notes?: string;
}
