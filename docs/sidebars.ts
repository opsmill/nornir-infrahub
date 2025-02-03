import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  nornirSidebar: [
    'nornir/readme',
    {
      type: 'category',
      label: 'Reference',
      items: [
        'nornir/references/plugins/infrahub_inventory',
        'nornir/references/plugins/artifact_tasks',
      ],
    }
  ]
};

export default sidebars;
