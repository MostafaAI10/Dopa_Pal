import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Code, BrainCircuit, Globe } from 'lucide-react';
import api from '../../services/api';

const TAG_ICONS = {
  cybersecurity: <Code className="w-5 h-5" />,
  neuroscience: <BrainCircuit className="w-5 h-5" />,
  programming: <Code className="w-5 h-5" />,
  languages: <Globe className="w-5 h-5" />,
};

const TAG_LABELS = {
  cybersecurity: 'Cybersecurity',
  neuroscience: 'Neuroscience',
  programming: 'Programming',
  languages: 'Languages',
};

const InterestVault = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getVaultDrops()
      .then(drops => {
        setItems(drops.map(d => ({
          id: d.id,
          tag: d.metadata_json?.tag || 'general',
          icon: TAG_ICONS[d.metadata_json?.tag] || <Sparkles className="w-5 h-5" />,
          content: d.metadata_json?.fact || '',
          date: d.unlocked_at ? new Date(d.unlocked_at).toLocaleDateString() : '',
          label: TAG_LABELS[d.metadata_json?.tag] || d.metadata_json?.tag || 'General',
        })));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl space-y-8">
        <div className="bg-gradient-to-br from-purple-500/10 to-accent/10 border border-accent/20 rounded-2xl p-8 relative overflow-hidden">
          <h2 className="text-2xl font-semibold text-text-primary mb-2">The Interest Vault</h2>
          <p className="text-text-secondary">Loading vault drops...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8">
      <div className="bg-gradient-to-br from-purple-500/10 to-accent/10 border border-accent/20 rounded-2xl p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Sparkles className="w-32 h-32 text-accent" />
        </div>
        <h2 className="text-2xl font-semibold text-text-primary mb-2">The Interest Vault</h2>
        <p className="text-text-secondary max-w-2xl">
          Rewards collected from completing focus blocks. Because dopamine shouldn't only come from checking boxes.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors rounded-2xl p-6 group"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2 text-accent/80 bg-accent/10 px-3 py-1.5 rounded-lg text-sm font-medium">
                {item.icon}
                <span>{item.label}</span>
              </div>
              <span className="text-xs text-text-secondary">{item.date}</span>
            </div>
            <p className="text-text-primary leading-relaxed text-sm group-hover:text-white transition-colors">
              {item.content}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default InterestVault;
