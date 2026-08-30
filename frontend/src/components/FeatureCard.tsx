import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';

interface FeatureCardProps {
  title: string;
  description: string;
  icon: string;
  actions: Array<{
    label: string;
    onClick: () => void;
    variant?: 'default' | 'outline' | 'secondary';
  }>;
  status?: 'active' | 'inactive' | 'processing';
}

export function FeatureCard({ title, description, icon, actions, status = 'inactive' }: FeatureCardProps) {
  const statusColors = {
    active: 'border-success bg-success',
    processing: 'border-warning bg-warning',
    inactive: 'border-gray-200 bg-white'
  };

  return (
    <Card className={`transition-all duration-300 hover:shadow-lg ${statusColors[status]}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <img src={icon} alt={title} className="w-8 h-8 object-contain" />
          <div>
            <CardTitle className="text-lg">{title}</CardTitle>
            <CardDescription className="text-sm">{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {actions.map((action, index) => (
            <Button
              key={index}
              variant={action.variant || 'outline'}
              size="sm"
              onClick={action.onClick}
              className="text-xs"
            >
              {action.label}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}