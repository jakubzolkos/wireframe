import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useNavigate, useLocation } from 'react-router-dom';
import { Cpu, ArrowRight, Zap, FileText, Database, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';
import { z } from 'zod';

const authSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email address' }),
  password: z.string().min(6, { message: 'Password must be at least 6 characters' }),
});

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn, signUp, user, isLoading } = useAuth();

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  // Redirect if already logged in
  useEffect(() => {
    if (user && !isLoading) {
      navigate(from, { replace: true });
    }
  }, [user, isLoading, navigate, from]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Validate inputs
    const validation = authSchema.safeParse({ email, password });
    if (!validation.success) {
      const fieldErrors: { email?: string; password?: string } = {};
      validation.error.errors.forEach((err) => {
        if (err.path[0] === 'email') fieldErrors.email = err.message;
        if (err.path[0] === 'password') fieldErrors.password = err.message;
      });
      setErrors(fieldErrors);
      return;
    }

    setIsSubmitting(true);

    try {
      if (isLogin) {
        const { error } = await signIn(email, password);
        if (error) {
          if (error.message.includes('Invalid login credentials')) {
            toast.error('Invalid credentials', {
              description: 'Please check your email and password.',
            });
          } else {
            toast.error('Sign in failed', {
              description: error.message,
            });
          }
        } else {
          toast.success('Welcome back!');
          navigate(from, { replace: true });
        }
      } else {
        const { error } = await signUp(email, password);
        if (error) {
          if (error.message.includes('already registered')) {
            toast.error('Account exists', {
              description: 'This email is already registered. Try signing in instead.',
            });
          } else {
            toast.error('Sign up failed', {
              description: error.message,
            });
          }
        } else {
          toast.success('Account created!', {
            description: 'You can now access your dashboard.',
          });
          navigate(from, { replace: true });
        }
      }
    } catch (err) {
      toast.error('Something went wrong', {
        description: 'Please try again later.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

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
                  className={`h-12 bg-secondary border-border focus:border-primary focus:ring-primary ${errors.email ? 'border-destructive' : ''}`}
                  disabled={isSubmitting}
                />
                {errors.email && (
                  <p className="text-sm text-destructive">{errors.email}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`h-12 bg-secondary border-border focus:border-primary focus:ring-primary ${errors.password ? 'border-destructive' : ''}`}
                  disabled={isSubmitting}
                />
                {errors.password && (
                  <p className="text-sm text-destructive">{errors.password}</p>
                )}
              </div>

              <Button type="submit" variant="glow" size="xl" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    {isLogin ? 'Signing in...' : 'Creating account...'}
                  </>
                ) : (
                  <>
                    {isLogin ? 'Sign in' : 'Create account'}
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </Button>
            </form>

            <div className="mt-8 text-center">
              <p className="text-muted-foreground">
                {isLogin ? "Don't have an account?" : 'Already have an account?'}
                <button
                  type="button"
                  onClick={() => {
                    setIsLogin(!isLogin);
                    setErrors({});
                  }}
                  className="ml-2 text-primary hover:underline font-medium"
                  disabled={isSubmitting}
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
