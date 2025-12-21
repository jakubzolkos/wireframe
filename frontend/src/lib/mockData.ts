export interface Design {
  id: string;
  name: string;
  partNumber: string;
  manufacturer: string;
  status: 'processing' | 'completed' | 'failed';
  uploadedAt: Date;
  completedAt?: Date;
  bomItems?: BOMItem[];
  schematicUrl?: string;
}

export interface DatasheetSource {
  page: number;
  section: string;
  excerpt: string;
}

export interface BOMItem {
  id: string;
  reference: string;
  partNumber: string;
  manufacturer: string;
  description: string;
  quantity: number;
  package?: string;
  value?: string;
  source?: DatasheetSource;
}

export const mockDesigns: Design[] = [
  {
    id: '1',
    name: 'LTC3780 Buck-Boost Controller',
    partNumber: 'LTC3780',
    manufacturer: 'Analog Devices',
    status: 'completed',
    uploadedAt: new Date('2024-01-15'),
    completedAt: new Date('2024-01-15'),
    bomItems: [
      { id: '1', reference: 'U1', partNumber: 'LTC3780EGN-PBF', manufacturer: 'Analog Devices', description: 'Buck-Boost DC/DC Controller', quantity: 1, package: 'SSOP-24', source: { page: 1, section: 'Ordering Information', excerpt: 'LTC3780EGN-PBF is the lead-free SSOP-24 package variant' } },
      { id: '2', reference: 'L1', partNumber: 'SER2915H-223KL', manufacturer: 'Coilcraft', description: '22µH Inductor', quantity: 1, package: 'SER2915H', source: { page: 18, section: 'Typical Application', excerpt: 'L1: 22µH inductor, Coilcraft SER2915H-223KL recommended for saturation current >10A' } },
      { id: '3', reference: 'Q1,Q2', partNumber: 'Si7336ADP', manufacturer: 'Vishay', description: 'N-Channel MOSFET 30V', quantity: 2, package: 'PowerPAK SO-8', source: { page: 15, section: 'Power MOSFET Selection', excerpt: 'For VIN up to 28V, use 30V N-Channel MOSFETs with RDS(ON) < 10mΩ' } },
      { id: '4', reference: 'C1,C2', partNumber: 'GRM32ER71H106KA12L', manufacturer: 'Murata', description: '10µF 50V X7R', quantity: 2, package: '1210', source: { page: 19, section: 'Input Capacitor Selection', excerpt: 'CIN: 10µF minimum, X7R or X5R ceramic, voltage rating > VIN(MAX)' } },
      { id: '5', reference: 'R1', partNumber: 'CRCW060310K0FKEA', manufacturer: 'Vishay', description: '10kΩ 1% 0.1W', quantity: 1, package: '0603', source: { page: 12, section: 'Compensation Network', excerpt: 'RC = 10kΩ sets the loop crossover frequency to approximately 20kHz' } },
    ],
  },
  {
    id: '2',
    name: 'TPS65988 USB-C PD Controller',
    partNumber: 'TPS65988',
    manufacturer: 'Texas Instruments',
    status: 'completed',
    uploadedAt: new Date('2024-01-14'),
    completedAt: new Date('2024-01-14'),
    bomItems: [
      { id: '1', reference: 'U1', partNumber: 'TPS65988DHRSHR', manufacturer: 'Texas Instruments', description: 'USB Type-C PD Controller', quantity: 1, package: 'WQFN-56', source: { page: 2, section: 'Package Options', excerpt: 'TPS65988DHRSHR: 56-pin WQFN package, 8mm x 8mm' } },
      { id: '2', reference: 'C1-C4', partNumber: 'CL10A106KP8NNNC', manufacturer: 'Samsung', description: '10µF 10V X5R', quantity: 4, package: '0603', source: { page: 45, section: 'Decoupling Capacitors', excerpt: 'Place four 10µF X5R capacitors close to VDD pins' } },
      { id: '3', reference: 'R1,R2', partNumber: 'RC0603FR-075K1L', manufacturer: 'Yageo', description: '5.1kΩ 1%', quantity: 2, package: '0603', source: { page: 38, section: 'CC Line Configuration', excerpt: 'Use 5.1kΩ pull-down resistors on CC1 and CC2 for DFP mode' } },
    ],
  },
  {
    id: '3',
    name: 'AD9361 RF Transceiver',
    partNumber: 'AD9361',
    manufacturer: 'Analog Devices',
    status: 'processing',
    uploadedAt: new Date('2024-01-16'),
  },
  {
    id: '4',
    name: 'MAX17055 Fuel Gauge',
    partNumber: 'MAX17055',
    manufacturer: 'Analog Devices',
    status: 'failed',
    uploadedAt: new Date('2024-01-13'),
  },
];
