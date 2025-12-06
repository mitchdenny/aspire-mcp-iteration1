# Copilot instructions

This repository is set up to use Aspire. Aspire is an orchestrator for the entire application and will take care of configuring dependencies, building, and running the application. The resources that make up the application are defined in `apphost.cs` including applicaiton code and external dependencies.

To run the application run the following command:

```
aspire run
```

If there is already an instance of the application running it will prompt to stop the existing instance. Generally you only need to restart the application if code in `apphost.cs` is changed, but if you experience problems it can be useful to reset everything to the starting state.

To restart individual resources within the application use the _list resources_ tool to find the resource and then use the _execute resource command_ tool to restart it.

The following additional aspire related tools are available and you should use them for diagnostics and configuring more resources in the app model as needed.

1. select apphost; use this tool if working with multiple app hosts within a workspace.
2. list apphosts; use this tool to get details about active app hosts.
3. list integrations; use this tool to get details about available integrations.
4. get integration docs; use this tool to retrieve documentation for a specific integration.
5. list structured logs; use this tool to get details about structured logs.
6. list console logs; use this tool to get details about console logs.
7. list traces; use this tool to get details about traces.
8. list trace structured logs; use this tool to get logs related to a trace

The playwright MCP server has also been configured in this repository and you should use it to perform functional investigations of the resources defined in the app model as you work on the codebase. To get endpoints that can be used for navigation using the playwright MCP server use the list resources tool.