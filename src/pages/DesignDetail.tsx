import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { ArrowLeft, Download, FileText, Cpu, Package, Copy, ExternalLink, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getJobStatus, downloadSchematic, downloadBOM, type FinalDesignResponse } from '@/lib/api';

const DesignDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [design, setDesign] = useState<FinalDesignResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<string>('');

  useEffect(() => {
    if (id) {
      loadDesign(id);
    }
  }, [id]);

  const loadDesign = async (jobId: string) => {
    try {
      setLoading(true);
      const response = await getJobStatus(jobId);
      setStatus(response.status);
      if (response.design) {
        setDesign(response.design);
      }
    } catch (error) {
      toast.error('Failed to load design', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!design) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Design not found</h2>
          <p className="text-muted-foreground mb-4">Status: {status}</p>
          <Button variant="outline" onClick={() => navigate('/dashboard')}>
            Return to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const handleDownloadSchematic = () => {
    if (id) {
      downloadSchematic(id);
      toast.success('Downloading KiCad schematic...');
    }
  };

  const handleDownloadBOM = () => {
    if (id) {
      downloadBOM(id);
      toast.success('Downloading BOM...');
    }
  };

  const handleCopyPartNumber = (pn: string) => {
    navigator.clipboard.writeText(pn);
    toast.success('Copied to clipboard', { description: pn });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-semibold">{design.metadata.device_name || 'Design'}</h1>
              <p className="text-sm font-mono text-primary">{design.metadata.datasheet_title || id}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={handleDownloadBOM}>
              <Download className="w-4 h-4" />
              Export BOM
            </Button>
            <Button variant="glow" onClick={handleDownloadSchematic}>
              <Download className="w-4 h-4" />
              Download Schematic
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-card border border-border rounded-xl p-5 animate-fade-in">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Cpu className="w-5 h-5 text-primary" />
              </div>
              <span className="text-sm text-muted-foreground">Part Number</span>
            </div>
            <p className="font-mono text-lg font-semibold">{design.metadata.datasheet_title || 'N/A'}</p>
          </div>

          <div className="bg-card border border-border rounded-xl p-5 animate-fade-in" style={{ animationDelay: '100ms' }}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <FileText className="w-5 h-5 text-primary" />
              </div>
              <span className="text-sm text-muted-foreground">Status</span>
            </div>
            <p className="text-lg font-semibold">{design.status}</p>
          </div>

          <div className="bg-card border border-border rounded-xl p-5 animate-fade-in" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Package className="w-5 h-5 text-primary" />
              </div>
              <span className="text-sm text-muted-foreground">Components</span>
            </div>
            <p className="text-lg font-semibold">{design.bom.length} items</p>
          </div>
        </div>

        {/* Tabs Content */}
        <Tabs defaultValue="bom" className="animate-fade-in" style={{ animationDelay: '300ms' }}>
          <TabsList className="bg-secondary border border-border mb-6">
            <TabsTrigger value="schematic">Schematic Preview</TabsTrigger>
            <TabsTrigger value="bom">Bill of Materials</TabsTrigger>
          </TabsList>

          <TabsContent value="schematic">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="aspect-video bg-dot-pattern flex items-center justify-center">
                <div className="text-center">
                  <div className="p-4 bg-secondary/50 rounded-xl border border-border mb-4 inline-block">
                    <Cpu className="w-16 h-16 text-primary/50" />
                  </div>
                  <p className="text-muted-foreground">Schematic preview will appear here</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Download the .kicad_sch file to view in KiCad
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="bom">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-24">Reference</TableHead>
                    <TableHead>Part Number</TableHead>
                    <TableHead>Manufacturer</TableHead>
                    <TableHead className="hidden md:table-cell">Description</TableHead>
                    <TableHead className="hidden lg:table-cell">Package</TableHead>
                    <TableHead className="w-20 text-center">Qty</TableHead>
                    <TableHead className="w-24"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {design.bom.map((item, index: number) => (
                    <TableRow 
                      key={`${item.reference}-${index}`}
                      className="animate-fade-in"
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      <TableCell className="font-mono text-primary font-medium">
                        {item.reference}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm">{item.part_number || 'N/A'}</span>
                          {item.part_number && (
                            <button
                              onClick={() => handleCopyPartNumber(item.part_number!)}
                              className="p-1 hover:bg-secondary rounded transition-colors"
                            >
                              <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                            </button>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{item.manufacturer || 'N/A'}</TableCell>
                      <TableCell className="hidden md:table-cell text-muted-foreground max-w-xs truncate">
                        {item.description || 'N/A'}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell font-mono text-sm text-muted-foreground">
                        {item.package || 'N/A'}
                      </TableCell>
                      <TableCell className="text-center font-medium">{item.quantity}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" className="gap-1">
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">Find</span>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default DesignDetail;
