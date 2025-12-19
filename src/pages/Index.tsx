import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Cpu, ArrowRight, Zap, FileText, Database, CheckCircle2 } from 'lucide-react';

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Background Effects */}
      <div className="fixed inset-0 bg-grid-pattern opacity-20" />
      <div className="fixed inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5" />
      
      {/* Header */}
      <header className="relative z-10 container mx-auto px-6 py-6">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/30 shadow-[0_0_15px_hsl(187_92%_50%/0.2)]">
              <Cpu className="w-6 h-6 text-primary" />
            </div>
            <span className="text-xl font-semibold tracking-tight">SchematicAI</span>
          </div>
          
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/auth')}>
              Sign in
            </Button>
            <Button variant="glow" onClick={() => navigate('/auth')}>
              Get Started
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 container mx-auto px-6">
        <div className="max-w-4xl mx-auto text-center pt-20 pb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary border border-border mb-8 animate-fade-in">
            <Zap className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">AI-Powered Reference Design Extraction</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold leading-tight mb-6 animate-fade-in" style={{ animationDelay: '100ms' }}>
            Transform IC Datasheets into
            <span className="text-gradient block mt-2">Production-Ready Designs</span>
          </h1>
          
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 animate-fade-in" style={{ animationDelay: '200ms' }}>
            Upload datasheets from Analog Devices, Texas Instruments, and more. 
            Get accurate KiCad schematics and complete BOMs in minutes.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in" style={{ animationDelay: '300ms' }}>
            <Button variant="glow" size="xl" onClick={() => navigate('/auth')}>
              Start Converting
              <ArrowRight className="w-5 h-5" />
            </Button>
            <Button variant="outline" size="xl" onClick={() => navigate('/auth')}>
              View Demo
            </Button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto pb-20">
          {[
            {
              icon: FileText,
              title: 'Smart PDF Parsing',
              description: 'Advanced LLM extracts reference designs, manufacturer part numbers, and circuit topology from complex datasheets.',
            },
            {
              icon: Cpu,
              title: 'KiCad Schematic Output',
              description: 'Generate production-ready .kicad_sch files with proper symbols, net connections, and annotations.',
            },
            {
              icon: Database,
              title: 'Complete BOM Generation',
              description: 'Accurate bill of materials with manufacturer PNs, descriptions, packages, and quantities.',
            },
          ].map((feature, index) => (
            <div
              key={feature.title}
              className="group bg-card border border-border rounded-xl p-6 hover:border-primary/50 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 animate-fade-in"
              style={{ animationDelay: `${400 + index * 100}ms` }}
            >
              <div className="p-3 bg-secondary rounded-lg w-fit mb-4 group-hover:bg-primary/10 transition-colors">
                <feature.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>

        {/* Supported Vendors */}
        <div className="text-center pb-20 animate-fade-in" style={{ animationDelay: '700ms' }}>
          <p className="text-sm text-muted-foreground mb-6">Supports datasheets from leading IC vendors</p>
          <div className="flex flex-wrap items-center justify-center gap-8 text-muted-foreground">
            {['Analog Devices', 'Texas Instruments', 'Maxim', 'STMicroelectronics', 'NXP', 'Microchip'].map((vendor) => (
              <div key={vendor} className="flex items-center gap-2 opacity-60 hover:opacity-100 transition-opacity">
                <CheckCircle2 className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">{vendor}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
