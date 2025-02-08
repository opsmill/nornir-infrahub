import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  nornirSidebar: [
    'readme',
    {
      type: 'category',
      label: 'Nornir Plugin Reference',
      items: [
        'references/plugins/infrahub_inventory',
        'references/plugins/artifact_tasks',
      ],
    }
  ]
};

export default sidebars;
