import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Cpu, Plus, Search, LayoutGrid, List } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import UploadZone from '@/components/UploadZone';
import DesignCard from '@/components/DesignCard';
import UserMenu from '@/components/UserMenu';
import { mockDesigns } from '@/lib/mockData';
import { cn } from '@/lib/utils';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

const Dashboard = () => {
  const navigate = useNavigate();
  const { signOut } = useAuth();
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const handleFileSelect = async (file: File) => {
    setIsProcessing(true);
    try {
      // Mock processing for now
      await new Promise(resolve => setTimeout(resolve, 1500));
      setIsUploadOpen(false);
      toast.success('Datasheet uploaded successfully', {
        description: 'Processing will begin shortly.',
      });
    } catch (error) {
      toast.error('Upload failed', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    toast.success('Signed out successfully');
    navigate('/');
  };

  const filteredDesigns = mockDesigns.filter(design =>
    design.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    design.partNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
    design.manufacturer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const stats = {
    total: mockDesigns.length,
    completed: mockDesigns.filter(d => d.status === 'completed').length,
    processing: mockDesigns.filter(d => d.status === 'processing').length,
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/30">
              <Cpu className="w-5 h-5 text-primary" />
            </div>
            <span className="text-lg font-semibold">Wireframe</span>
          </div>

          <div className="flex items-center gap-4">
            <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
              <DialogTrigger asChild>
                <Button variant="glow">
                  <Plus className="w-4 h-4" />
                  New Design
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Upload Datasheet</DialogTitle>
                </DialogHeader>
                <UploadZone onFileSelect={handleFileSelect} isProcessing={isProcessing} />
              </DialogContent>
            </Dialog>

            <UserMenu onSignOut={handleSignOut} />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {[
            { label: 'Total Designs', value: stats.total, color: 'text-foreground' },
            { label: 'Completed', value: stats.completed, color: 'text-success' },
            { label: 'Processing', value: stats.processing, color: 'text-warning' },
          ].map((stat, index) => (
            <div
              key={stat.label}
              className="bg-card border border-border rounded-xl p-5 animate-fade-in"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <p className="text-sm text-muted-foreground mb-1">{stat.label}</p>
              <p className={cn("text-3xl font-bold", stat.color)}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              placeholder="Search designs by name, part number, or manufacturer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-11 bg-secondary border-border"
            />
          </div>

          <div className="flex items-center gap-1 bg-secondary rounded-lg p-1 border border-border">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                "p-2 rounded-md transition-colors",
                viewMode === 'grid' ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <LayoutGrid className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                "p-2 rounded-md transition-colors",
                viewMode === 'list' ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <List className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Designs Grid */}
        <div className={cn(
          "grid gap-4",
          viewMode === 'grid' ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" : "grid-cols-1"
        )}>
          {filteredDesigns.map((design, index) => (
            <div
              key={design.id}
              className="animate-fade-in"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <DesignCard design={design} />
            </div>
          ))}
        </div>

        {filteredDesigns.length === 0 && (
          <div className="text-center py-16">
            <p className="text-muted-foreground">No designs found matching your search.</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
