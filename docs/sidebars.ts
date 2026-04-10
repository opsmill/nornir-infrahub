import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  nornirSidebar: [
    'readme',
    'getting-started',
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/your-first-automation-workflow',
        'guides/configuring-schema-mappings',
      ],
    },
    {
      type: 'category',
      label: 'Topics',
      items: [
        'topics/understanding-nornir-infrahub-integration',
        'topics/infrahub-inventory-concepts',
        'topics/artifact-lifecycle-management',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'references/plugins/infrahub_inventory',
        'references/plugins/artifact_tasks',
        'references/plugins/file_object_tasks',
      ],
    }
  ]
};

export default sidebars;
