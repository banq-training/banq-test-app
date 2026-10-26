// Website hosting for the workshop: one Azure Container Apps environment that attendee
// repositories publish to from GitHub Actions, without any secret.
//
// Capacity: each website is its own container app with 0.25 CPU that sleeps when nobody visits
// (minReplicas 0, maxReplicas 1). 80 attendees with a production and a feature slot each are 160
// apps and at most 40 cores, well under the environment's consumption-core quota (500 when
// checked on 25 October 2026 with az containerapp env list-usages).
//
// Trust model: only the template's own publisher workflow (website-publisher.yml on the
// template's main branch), running for a repository owned by the GitHub organisation, can sign
// in as the deploy identity. Attendees never sign in to Azure and hold no credentials.
// Deploy and tear down: see the hosting notes in the presenter's private folder (HOSTING.md).

targetScope = 'resourceGroup'

@description('Azure region for every resource.')
param location string = resourceGroup().location

@description('Container Apps environment shared by all attendee websites.')
param environmentName string = 'cae-hackathon'

@description('Private registry for the website images (globally unique, 5-50 letters and digits).')
param registryName string = 'acrnnhackathon2026'

@description('Registry tier. Standard gives 100 GiB and more transfer speed than Basic for about USD 0.67 a day, so 80 attendees (160 websites with feature slots) can publish at once.')
param registrySku string = 'Standard'

@description('Log Analytics workspace for the environment, capped at 1 GB a day.')
param workspaceName string = 'log-nn-hackathon'

@description('Identity that GitHub Actions signs in as to build and publish websites.')
param deployIdentityName string = 'nn-hackathon-deploy'

@description('Identity the websites use to pull their own images; it can only pull.')
param pullIdentityName string = 'nn-hackathon-pull'

@description('GitHub organisation that owns the attendee repositories.')
param githubOrganization string = 'agentic-dev-labs'

@description('Immutable numeric ID of that organisation (gh api orgs/<name> --jq .id).')
param githubOrganizationId string = '323143564'

@description('The only workflow allowed to sign in: owner/repo/path@ref of the publisher.')
param publisherWorkflow string = 'agentic-dev-labs/copilot-hackathon-template/.github/workflows/website-publisher.yml@refs/heads/main'

@description('Tags applied to every resource so the workshop footprint is easy to find and remove.')
param tags object = {
  workshop: 'nn-hackathon-2026-10'
  purpose: 'attendee-websites'
}

var roleIds = {
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  acrPush: '8311e382-0749-4cb8-b61a-304f252e45ec'
  containerAppsContributor: '358470bc-b998-42bd-ab17-a7e34c199c0f'
  managedIdentityOperator: 'f1a07417-d97a-45cb-824c-7a7467783830'
  reader: 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: 1 }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// Keeps the environment's compute awake. With no running app, Azure suspended it (seen on
// 25 October 2026) and the first publish then waited about 13 minutes. One tiny always-on replica,
// about USD 0.20 a day, prevents that. It has no ingress and no repository tag, so the publisher
// never removes it, and an attendee cannot take its name.
resource keepWarm 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'keep-warm'
  location: location
  tags: union(tags, { role: 'keep-environment-awake' })
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    template: {
      containers: [
        {
          name: 'keep-warm'
          image: 'mcr.microsoft.com/k8se/quickstart:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: tags
  sku: { name: registrySku }
  properties: {
    adminUserEnabled: false
  }
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: pullIdentityName
  location: location
  tags: tags
}

resource deployIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: deployIdentityName
  location: location
  tags: tags
}

// A flexible federated identity credential: one trust for every attendee repository, still
// bound to the organisation's immutable ID, the main branch, and the template's publisher.
resource githubTrust 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2025-01-31-preview' = {
  parent: deployIdentity
  name: 'github-website-publisher'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    audiences: [
      'api://AzureADTokenExchange'
    ]
    claimsMatchingExpression: {
      value: 'claims[\'sub\'] matches \'repo:${githubOrganization}@${githubOrganizationId}/*:ref:refs/heads/main\' and claims[\'repository_owner_id\'] eq \'${githubOrganizationId}\' and claims[\'job_workflow_ref\'] eq \'${publisherWorkflow}\''
      languageVersion: 1
    }
  }
}

resource pullFromRegistry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, pullIdentity.id, roleIds.acrPull)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.acrPull)
    principalId: pullIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource pushToRegistry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, deployIdentity.id, roleIds.acrPush)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.acrPush)
    principalId: deployIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource manageWebsites 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, deployIdentity.id, roleIds.containerAppsContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.containerAppsContributor)
    principalId: deployIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource readGroup 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, deployIdentity.id, roleIds.reader)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.reader)
    principalId: deployIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource attachPullIdentity 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(pullIdentity.id, deployIdentity.id, roleIds.managedIdentityOperator)
  scope: pullIdentity
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.managedIdentityOperator)
    principalId: deployIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output environmentDefaultDomain string = environment.properties.defaultDomain
output environmentId string = environment.id
output registryLoginServer string = registry.properties.loginServer
output deployClientId string = deployIdentity.properties.clientId
output pullIdentityId string = pullIdentity.id
output tenantId string = subscription().tenantId
output subscriptionId string = subscription().subscriptionId
