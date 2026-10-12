// Mirrors of the backend Pydantic schemas (subset used by the UI).

export interface Variable {
  name: string;
  source?: "npm_last2" | "npm_last3" | "const" | "expr" | null;
  value?: number | null;
  expr?: string | null;
}

export interface EndDeviceSpec {
  type: string;
  count: string;
  name: string;
  dhcp: boolean;
}

export interface SubnetDef {
  name: string;
  end_devices: EndDeviceSpec[];
  wireless_to?: string | null;
}

export interface GradingConfig {
  auto: string[];
  manual: string[];
}

export interface CaseSchema {
  case_id: string;
  title: string;
  base_block: string;
  variables: Variable[];
  subnets: SubnetDef[];
  method: string;
  gateway_is_first_host?: boolean;
  order_tiebreak?: string;
  grading: GradingConfig;
}

export interface CaseSummary {
  case_id: string;
  title: string;
}

export interface DeviceType {
  code: string;
  label: string;
}

export interface ExpectedSubnet {
  name: string;
  network_address: string;
  broadcast_address: string;
  subnet_mask: string;
  prefix: number;
  max_end_devices: number;
  max_hosts: number;
  host_first: string;
  host_last: string;
  gateway: string;
  required_devices: Record<string, number>;
}

export interface SolveResult {
  case_id: string;
  npm: string;
  resolved_vars: Record<string, number>;
  subnets: ExpectedSubnet[];
  total_addresses_used: number;
  fits_base_block: boolean;
}

export interface StudentInterface {
  name: string;
  ip?: string | null;
  mask?: string | null;
  gateway?: string | null;
  status?: string;
  is_wireless?: boolean;
  ssid?: string | null;
  dhcp_enabled?: boolean;
}

export interface StudentDevice {
  id: string;
  name: string;
  type?: string | null;
  model?: string | null;
  power?: boolean;
  position?: Record<string, number> | null;
  interfaces: StudentInterface[];
  ip?: string | null;
  mask?: string | null;
  gateway?: string | null;
  dhcp_enabled?: boolean;
}

export interface StudentLink {
  from_device: string;
  from_interface?: string | null;
  to_device: string;
  to_interface?: string | null;
  type?: string | null;
  status?: string;
}

export interface StudentDhcpPool {
  router: string;
  interface?: string | null;
  name?: string | null;
  network?: string | null;
  mask?: string | null;
  default_gateway?: string | null;
  start_ip?: string | null;
  end_ip?: string | null;
}

export interface StudentNote {
  text: string;
  position?: Record<string, number> | null;
}

export interface StudentJSON {
  source_file?: string | null;
  devices: StudentDevice[];
  links: StudentLink[];
  dhcp_pools: StudentDhcpPool[];
  notes: StudentNote[];
}

export interface CheckResult {
  key: string;
  label: string;
  passed: boolean;
  fraction: number;
  score: number;
  max_score: number;
  detail: string;
  expected: string;
  actual: string;
}

export interface DeviceGrade {
  name: string;
  type: string;
  matched: boolean;
  checks: CheckResult[];
  score: number;
  max_score: number;
}

export interface SubnetGrade {
  name: string;
  checks: CheckResult[];
  device_grades: DeviceGrade[];
  score: number;
  max_score: number;
}

export interface GradeReport {
  case_id: string;
  npm: string;
  auto_score: number;
  auto_max: number;
  manual_items: string[];
  subnet_grades: SubnetGrade[];
  summary: string;
}
