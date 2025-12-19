import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useNavigate } from 'react-router-dom';
import { Cpu, ArrowRight, Zap, FileText, Database } from 'lucide-react';

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Mock authentication - navigate to dashboard
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-grid-pattern opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent/10" />
        
        <div className="relative z-10 flex flex-col justify-center px-16 xl:px-24">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-3 rounded-xl bg-primary/10 border border-primary/30 glow-primary">
              <Cpu className="w-8 h-8 text-primary" />
            </div>
            <span className="text-2xl font-semibold tracking-tight">SchematicAI</span>
          </div>
          
          <h1 className="text-4xl xl:text-5xl font-bold leading-tight mb-6">
            Transform Datasheets into
            <span className="text-gradient block mt-2">Production-Ready Designs</span>
          </h1>
          
          <p className="text-lg text-muted-foreground mb-12 max-w-md">
            Upload IC datasheets and get KiCad schematics with accurate BOMs. 
            Powered by advanced AI that understands reference designs.
          </p>

          <div className="space-y-4">
            {[
              { icon: FileText, text: 'Extract reference designs from PDFs' },
              { icon: Zap, text: 'Generate KiCad-compatible schematics' },
              { icon: Database, text: 'Accurate BOM with manufacturer PNs' },
            ].map((feature, index) => (
              <div 
                key={index}
                className="flex items-center gap-4 text-muted-foreground animate-fade-in"
                style={{ animationDelay: `${index * 150}ms` }}
              >
                <div className="p-2 rounded-lg bg-secondary border border-border">
                  <feature.icon className="w-5 h-5 text-primary" />
                </div>
                <span>{feature.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel - Auth Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/30 glow-primary">
              <Cpu className="w-6 h-6 text-primary" />
            </div>
            <span className="text-xl font-semibold">SchematicAI</span>
          </div>

          <div className="bg-card border border-border rounded-2xl p-8 shadow-xl animate-scale-in">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">
                {isLogin ? 'Welcome back' : 'Create account'}
              </h2>
              <p className="text-muted-foreground">
                {isLogin 
                  ? 'Sign in to access your designs' 
                  : 'Start converting datasheets today'}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="engineer@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-12 bg-secondary border-border focus:border-primary focus:ring-primary"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-12 bg-secondary border-border focus:border-primary focus:ring-primary"
                />
              </div>

              {isLogin && (
                <div className="text-right">
                  <button type="button" className="text-sm text-primary hover:underline">
                    Forgot password?
                  </button>
                </div>
              )}

              <Button type="submit" variant="glow" size="xl" className="w-full">
                {isLogin ? 'Sign in' : 'Create account'}
                <ArrowRight className="w-5 h-5" />
              </Button>
            </form>

            <div className="mt-8 text-center">
              <p className="text-muted-foreground">
                {isLogin ? "Don't have an account?" : 'Already have an account?'}
                <button
                  type="button"
                  onClick={() => setIsLogin(!isLogin)}
                  className="ml-2 text-primary hover:underline font-medium"
                >
                  {isLogin ? 'Sign up' : 'Sign in'}
                </button>
              </p>
            </div>
          </div>

          <p className="text-center text-sm text-muted-foreground mt-6">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
};

export default Auth;
