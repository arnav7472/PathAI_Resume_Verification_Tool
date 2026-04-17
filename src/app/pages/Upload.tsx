import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import { useVerification } from '../context/VerificationContext';
import { FileUp, Loader2 } from 'lucide-react';

export function Upload() {
  const navigate = useNavigate();
  const { runVerification } = useVerification();
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [formData, setFormData] = useState({
    name: '',
    role: '',
    description: ''
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      toast.success(`Attached: ${e.target.files[0].name}`);
    }
  };

  const startScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file && !formData.description.trim()) {
      toast.error('Resume file or pasted text is required');
      return;
    }

    setLoading(true);
    try {
      await runVerification({
        name: formData.name,
        role: formData.role,
        file: file,
        text: formData.description
      });
      toast.success('Verification complete');
      navigate('/summary');
    } catch (error) {
      toast.error('Unable to analyze resume right now.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-bold text-white mb-6">New Verification</h1>
      
      <form onSubmit={startScan} className="space-y-6">
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-[10px] uppercase font-bold text-slate-600">Candidate Full Name</label>
            <input 
              type="text" 
              required
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              placeholder="e.g. John Doe" 
              className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm focus:border-indigo-500 outline-none text-white" 
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] uppercase font-bold text-slate-600">Target Role</label>
            <input 
              type="text" 
              value={formData.role}
              onChange={(e) => setFormData({...formData, role: e.target.value})}
              placeholder="e.g. Senior Backend Engineer" 
              className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm focus:border-indigo-500 outline-none text-white" 
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-500">Candidate Resume (PDF/DOC)</label>
          <div 
            onClick={() => fileInputRef.current?.click()}
            className="w-full bg-slate-900 border border-slate-800 p-8 rounded text-sm text-center cursor-pointer hover:border-slate-700 transition-colors border-dashed"
          >
            <input 
              type="file" 
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
              accept=".pdf,.doc,.docx"
            />
            <FileUp className="w-6 h-6 text-slate-500 mx-auto mb-2" />
            <p className="text-slate-400">{file ? file.name : 'Drop resume here or click to browse'}</p>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-[10px] uppercase font-bold text-slate-600">Paste Resume Text</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Optional if you upload a file. Paste resume text here to analyze directly."
            className="min-h-40 w-full resize-y bg-slate-900 border border-slate-800 rounded px-3 py-3 text-sm focus:border-indigo-500 outline-none text-white"
          />
          <p className="text-[11px] text-slate-600">Upload a file or paste text. If both are provided, pasted text is used first.</p>
        </div>

        <button 
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-3 rounded font-bold text-sm hover:bg-indigo-500 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing resume...
            </>
          ) : 'Run Verification Scan'}
        </button>
      </form>
    </div>
  );
}
