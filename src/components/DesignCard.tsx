import { Design } from '@/lib/mockData';
import { Clock, CheckCircle2, AlertCircle, Loader2, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';

interface DesignCardProps {
  design: Design;
}

const statusConfig = {
  processing: {
    icon: Loader2,
    label: 'Processing',
    className: 'text-warning bg-warning/10 border-warning/30',
    iconClassName: 'animate-spin',
  },
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    className: 'text-success bg-success/10 border-success/30',
    iconClassName: '',
  },
  failed: {
    icon: AlertCircle,
    label: 'Failed',
    className: 'text-destructive bg-destructive/10 border-destructive/30',
    iconClassName: '',
  },
};

const DesignCard = ({ design }: DesignCardProps) => {
  const navigate = useNavigate();
  const status = statusConfig[design.status];
  const StatusIcon = status.icon;

  const handleClick = () => {
    if (design.status === 'completed') {
      navigate(`/design/${design.id}`);
    }
  };

  return (
    <div
      onClick={handleClick}
      className={cn(
        "group bg-card border border-border rounded-xl p-5 transition-all duration-300 h-full flex flex-col",
        "hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5",
        design.status === 'completed' && "cursor-pointer"
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-foreground truncate mb-1 group-hover:text-primary transition-colors">
            {design.name}
          </h3>
          <p className="text-sm font-mono text-primary/80">{design.partNumber}</p>
        </div>
        
        <div className={cn(
          "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border shrink-0 ml-2",
          status.className
        )}>
          <StatusIcon className={cn("w-3.5 h-3.5", status.iconClassName)} />
          {status.label}
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground mt-auto">
        <div className="flex items-center gap-4">
          <span>{design.manufacturer}</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            {design.uploadedAt.toLocaleDateString()}
          </span>
        </div>
        
        {design.status === 'completed' && (
          <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
        )}
      </div>

      {design.bomItems && (
        <div className="mt-4 pt-4 border-t border-border">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{design.bomItems.length}</span> components in BOM
          </p>
        </div>
      )}
    </div>
  );
};

export default DesignCard;
