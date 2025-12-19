import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  isProcessing?: boolean;
}

const UploadZone = ({ onFileSelect, isProcessing = false }: UploadZoneProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    disabled: isProcessing,
  });

  const handleClear = () => {
    setSelectedFile(null);
  };

  const handleUpload = () => {
    if (selectedFile) {
      onFileSelect(selectedFile);
    }
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-xl p-8 transition-all duration-300 cursor-pointer",
          "bg-secondary/30 hover:bg-secondary/50",
          isDragActive && "border-primary bg-primary/5 glow-primary",
          !isDragActive && "border-border hover:border-primary/50",
          isProcessing && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center text-center">
          <div className={cn(
            "p-4 rounded-full mb-4 transition-all duration-300",
            isDragActive ? "bg-primary/20" : "bg-secondary"
          )}>
            <Upload className={cn(
              "w-8 h-8 transition-colors",
              isDragActive ? "text-primary" : "text-muted-foreground"
            )} />
          </div>
          
          <h3 className="text-lg font-semibold mb-2">
            {isDragActive ? 'Drop your datasheet here' : 'Upload IC Datasheet'}
          </h3>
          <p className="text-muted-foreground text-sm max-w-xs">
            Drag and drop a PDF datasheet, or click to browse. 
            We'll extract the reference design and generate your schematic.
          </p>
        </div>
      </div>

      {selectedFile && (
        <div className="flex items-center gap-4 p-4 bg-secondary rounded-lg border border-border animate-fade-in">
          <div className="p-2 bg-primary/10 rounded-lg">
            <FileText className="w-6 h-6 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{selectedFile.name}</p>
            <p className="text-sm text-muted-foreground">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          {!isProcessing && (
            <button
              onClick={handleClear}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          )}
        </div>
      )}

      {selectedFile && (
        <Button
          onClick={handleUpload}
          disabled={isProcessing}
          variant="glow"
          size="lg"
          className="w-full"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Processing Datasheet...
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              Generate Schematic & BOM
            </>
          )}
        </Button>
      )}
    </div>
  );
};

export default UploadZone;
