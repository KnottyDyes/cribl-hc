import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button, Input, Select } from '../common'
import type { UITheme } from '../../api/types'
import { uiThemeSchema } from '../../lib/validation'
import { useBranding } from '../../hooks/useBranding'

import { UseFormRegister } from 'react-hook-form'

const FONT_FAMILY_OPTIONS = [
  { value: 'system-ui', label: 'System Default' },
  { value: 'Inter, system-ui, -apple-system, sans-serif', label: 'Modern Sans' },
  { value: 'Georgia, serif', label: 'Serif' },
  { value: 'Monaco, Consolas, monospace', label: 'Monospace' },
]

const ColorInput = ({ theme, color, label, register }: {
  theme: 'light' | 'dark';
  color: keyof UITheme['light'];
  label: string;
  register: UseFormRegister<UITheme>;
}) => (
  <Input
    label={label}
    type="color"
    {...register(`${theme}.${color}`)}
    className="w-full"
  />
);

export function ThemeColorsForm() {
  const { branding, updateTheme, isUpdatingTheme } = useBranding()

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { isDirty },
  } = useForm<UITheme>({
    resolver: zodResolver(uiThemeSchema),
    defaultValues: branding.theme,
  })

  useEffect(() => {
    reset(branding.theme)
  }, [branding.theme, reset])

  const onSubmit = (data: UITheme) => {
    updateTheme(data)
  }
  
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Controller
            name="default_mode"
            control={control}
            render={({ field }) => (
                <Select
                    label="Default Theme Mode"
                    options={[
                        { value: 'system', label: 'System (Follow OS Preference)' },
                        { value: 'light', label: 'Light Mode' },
                        { value: 'dark', label: 'Dark Mode' },
                    ]}
                    {...field}
                />
            )}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div>
            <h4 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Light Theme Colors
            </h4>
            <div className="grid grid-cols-2 gap-4">
                <ColorInput theme="light" color="primary" label="Primary" register={register}/>
                <ColorInput theme="light" color="secondary" label="Secondary" register={register}/>
                <ColorInput theme="light" color="accent" label="Accent" register={register}/>
                <ColorInput theme="light" color="background" label="Background" register={register}/>
            </div>
          </div>

          <div>
            <h4 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Dark Theme Colors
            </h4>
            <div className="grid grid-cols-2 gap-4">
                <ColorInput theme="dark" color="primary" label="Primary" register={register}/>
                <ColorInput theme="dark" color="secondary" label="Secondary" register={register}/>
                <ColorInput theme="dark" color="accent" label="Accent" register={register}/>
                <ColorInput theme="dark" color="background" label="Background" register={register}/>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div>
             <Controller
                name="font_family"
                control={control}
                render={({ field }) => (
                    <Select
                        label="Font Family"
                        options={FONT_FAMILY_OPTIONS}
                        {...field}
                    />
                )}
             />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Border Radius
            </label>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Default"
                placeholder="0.5rem"
                {...register('border_radius')}
              />
              <Input
                label="Large"
                placeholder="0.75rem"
                {...register('border_radius_lg')}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button type="submit" loading={isUpdatingTheme} disabled={!isDirty || isUpdatingTheme}>
            Save Theme Settings
          </Button>
        </div>
      </form>
  )
}