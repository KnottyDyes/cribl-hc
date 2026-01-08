import type { CriblProduct } from '../../api/types'

interface ProductSelectorProps {
  selectedProducts: CriblProduct[] | undefined
  onChange: (products: CriblProduct[] | undefined) => void
}

const PRODUCTS: { value: CriblProduct; label: string }[] = [
  { value: 'stream', label: 'Stream' },
  { value: 'edge', label: 'Edge' },
  { value: 'lake', label: 'Lake' },
  { value: 'search', label: 'Search' },
]

export function ProductSelector({ selectedProducts, onChange }: ProductSelectorProps) {
  const isAllSelected = !selectedProducts || selectedProducts.length === 0

  const handleToggleAll = () => {
    if (!isAllSelected) {
      onChange(undefined)
    }
  }

  const handleToggleProduct = (product: CriblProduct) => {
    const current = isAllSelected ? [] : selectedProducts || []
    const isSelected = current.includes(product)

    let newSelection: CriblProduct[] | undefined

    if (isSelected) {
      newSelection = current.filter((p) => p !== product)
      if (newSelection.length === 0) {
        newSelection = undefined
      }
    } else {
      newSelection = [...current, product]
      if (newSelection.length === PRODUCTS.length) {
        newSelection = undefined
      }
    }
    onChange(newSelection)
  }

  const basePillClasses =
    'px-3 py-1.5 rounded-full text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors'
  const unselectedPillClasses =
    'bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600'
  const selectedPillClasses = 'bg-blue-600 border border-blue-600 text-white'

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        Select Products
      </label>
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleToggleAll}
            className={`${basePillClasses} ${isAllSelected ? selectedPillClasses : unselectedPillClasses}`}
          >
            All Products
          </button>
          {PRODUCTS.map((product) => {
            const isSelected = !isAllSelected && (selectedProducts?.includes(product.value) ?? false)
            return (
              <button
                key={product.value}
                type="button"
                onClick={() => handleToggleProduct(product.value)}
                className={`${basePillClasses} ${isSelected ? selectedPillClasses : unselectedPillClasses}`}
              >
                {product.label}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
