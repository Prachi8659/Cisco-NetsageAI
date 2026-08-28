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

export type AnalysisStatus = 'SUCCESS' | 'PARTIAL' | 'UNAVAILABLE' | 'FAILED' | 'UNKNOWN';

export type RuleSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type RuleStatus = 'DETECTED' | 'NO_FAULT' | 'INSUFFICIENT_EVIDENCE';

export interface DeviceFact {
  name: string;
  device_type: string;
  model?: string | null;
  hostname?: string | null;
  is_network_device?: boolean;
  category?: string;
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
  is_connected?: boolean;
  duplex?: string | null;
  speed?: string | null;
  mtu?: number | null;
  bandwidth_kbps?: number | null;
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
  ports?: string[];
  source: FactSource;
}

export interface RouteFact {
  device: string;
  network: string;
  mask?: string | null;
  next_hop?: string | null;
  interface?: string | null;
  protocol?: string | null;
  admin_distance?: number | null;
  metric?: number | null;
  is_default?: boolean;
  source: FactSource;
}

export interface GatewayFact {
  device: string;
  gateway_ip?: string | null;
  source: FactSource;
}

export interface TrunkFact {
  device: string;
  port: string;
  mode?: string | null;
  encapsulation?: string | null;
  status?: string | null;
  native_vlan?: number | null;
  allowed_vlans?: string | null;
  active_vlans?: string | null;
  source: FactSource;
}

export interface AclRule {
  action: string;
  protocol?: string | null;
  source: string;
  source_wildcard?: string | null;
  destination?: string | null;
  destination_wildcard?: string | null;
  port?: string | null;
  matches?: number | null;
  raw_rule: string;
}

export interface AclFact {
  device: string;
  acl_name_or_number: string;
  acl_type: string;
  rules: AclRule[];
  source: FactSource;
}

export interface DhcpBindingFact {
  device: string;
  ip_address: string;
  mac_address: string;
  lease_expiration?: string | null;
  binding_type: string;
  source: FactSource;
}

export interface DhcpPoolFact {
  device: string;
  pool_name: string;
  network?: string | null;
  mask?: string | null;
  default_router?: string | null;
  dns_server?: string | null;
  domain_name?: string | null;
  lease_time?: string | null;
  source: FactSource;
}

export interface MacEntryFact {
  device: string;
  vlan_id?: number | null;
  mac_address: string;
  entry_type: string;
  port: string;
  source: FactSource;
}

export interface NormalizedNetworkFacts {
  devices: DeviceFact[];
  interfaces: InterfaceFact[];
  connections: ConnectionFact[];
  vlans: VlanFact[];
  routes: RouteFact[];
  gateways: GatewayFact[];
  trunks?: TrunkFact[];
  acls?: AclFact[];
  dhcp_bindings?: DhcpBindingFact[];
  dhcp_pools?: DhcpPoolFact[];
  mac_entries?: MacEntryFact[];
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

export interface CiscoEvidence {
  id: number;
  case_id: number;
  device: string;
  command: string;
  raw_output: string;
  parser_status: string;
  parsed_facts?: NormalizedNetworkFacts | null;
  warnings?: string[] | null;
  created_at: string;
}

export interface CiscoEvidenceCreateInput {
  device: string;
  command: string;
  raw_output: string;
}

export interface RuleFinding {
  rule_id: string;
  fault_type: string;
  severity: RuleSeverity;
  device: string;
  interface?: string | null;
  description: string;
  evidence: string;
  suggested_correction: string;
  confidence: number;
  source: string;
  status: RuleStatus;
}

export interface RuleEngineResult {
  case_id: number;
  total_rules_evaluated: number;
  faults_detected: RuleFinding[];
  insufficient_evidence: RuleFinding[];
  no_fault_rules: string[];
  summary: string;
  evaluated_at: string;
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
  evidence?: CiscoEvidence[];
}

export interface CaseCreateInput {
  case_number?: string;
  title: string;
  category: string;
  severity: SeverityLevel;
  symptom: string;
  topology_notes?: string;
}

export type AiDiagnosisStatus = 
  | 'SUCCESS' 
  | 'INSUFFICIENT_EVIDENCE' 
  | 'AI_UNAVAILABLE' 
  | 'FAILED';

export interface AiDiagnosisResult {
  case_id: number;
  status: AiDiagnosisStatus;
  root_cause?: string | null;
  fault_type?: string | null;
  affected_device?: string | null;
  affected_interface?: string | null;
  evidence: string[];
  explanation?: string | null;
  recommended_correction?: string | null;
  confidence: number;
  reasoning_summary?: string | null;
  model_name: string;
  evaluated_at: string;
}

export type ComparisonStatus = 
  | 'AGREEMENT' 
  | 'DISAGREEMENT' 
  | 'PYTHON_ONLY' 
  | 'AI_ONLY' 
  | 'INSUFFICIENT_EVIDENCE';

export interface DiagnosisComparisonResult {
  case_id: number;
  status: ComparisonStatus;
  verdict_title: string;
  explanation: string;
  recommended_action: string;
  confidence_score: number;
  aligned_fault_type?: string | null;
  aligned_device?: string | null;
  aligned_interface?: string | null;
  human_review_required: boolean;
  python_summary: string;
  ai_summary: string;
  python_result?: RuleEngineResult | null;
  ai_result?: AiDiagnosisResult | null;
  compared_at: string;
}

export type ReviewDecision = 'ACCEPT' | 'REJECT' | 'NEEDS_REVIEW';

export type VerificationStatus = 'PENDING' | 'RESOLVED' | 'STILL_PRESENT' | 'INSUFFICIENT_EVIDENCE';

export interface HumanReviewRecord {
  id: number;
  case_id: number;
  decision: ReviewDecision;
  reviewer_name: string;
  reviewer_notes?: string | null;
  remediation_confirmed: boolean;
  remediation_notes?: string | null;
  remediation_applied_at?: string | null;
  verification_status: VerificationStatus;
  previous_fault_type?: string | null;
  previous_fault_device?: string | null;
  verification_findings?: any;
  verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface HumanReviewCreateInput {
  decision: ReviewDecision;
  reviewer_name: string;
  reviewer_notes?: string;
  previous_fault_type?: string;
  previous_fault_device?: string;
}

export interface VerificationResponse {
  review_id: number;
  case_id: number;
  verification_status: VerificationStatus;
  verdict_message: string;
  before_fault?: string | null;
  after_findings_count: number;
  remaining_faults: any[];
  verified_at: string;
}
